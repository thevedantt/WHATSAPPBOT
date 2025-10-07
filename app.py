import os
import time
import requests
from collections import defaultdict, deque
from flask import Flask, request, Response, send_file, send_from_directory
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client as TwilioClient
from openai import OpenAI
from google import genai
import logging
from murf import Murf
from threading import Thread
from gtts import gTTS

# -----------------------------
# Logging setup
# -----------------------------
logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] %(message)s')

# -----------------------------
# Secrets loader
# -----------------------------
def load_keys_from_file(path: str = "key.txt") -> None:
    try:
        if not os.path.exists(path):
            logging.warning(f"Key file not found: {path}")
            return
        with open(path, "r", encoding="utf-8") as fh:
            for raw_line in fh:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if key and value and key not in os.environ:
                    os.environ[key] = value
    except Exception as e:
        logging.error(f"Failed to load keys from {path}: {e}")

# -----------------------------
# Configuration
# -----------------------------
load_keys_from_file()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "")

GPT_CLIENT = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY", "")
)

GEMINI_CLIENT = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))

# Prefer environment variable only (no hardcoded fallback)
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY", "")
ASSEMBLYAI_BASE_URL = "https://api.assemblyai.com/v2"

MURF_API_KEY = os.getenv("MURF_API_KEY", "")
MURF_SDK_CLIENT = Murf(api_key=os.getenv("MURF_SDK_API_KEY", MURF_API_KEY))

BOT_PERSONA = "You are a friendly WhatsApp assistant. Answer clearly and briefly."
MAX_HISTORY = 6
THANK_YOU_SUFFIX = " — Thanks for chatting!"
CONTINUE_YES = {"y", "yes", "yeah", "yep"}
CONTINUE_NO = {"n", "no", "nope"}
FAREWELL_WORDS = {
    "bye", "goodbye", "thanks", "thank you", "thx", "bye bye",
    "see you", "see ya", "end", "stop", "exit", "good night",
    "goodnight", "take care"
}

app = Flask(__name__)

# In-memory conversation storage
conversations = defaultdict(lambda: deque(maxlen=MAX_HISTORY))
user_states = {}

# Ensure audio output directory exists and filenames are safe
AUDIO_OUTPUT_DIR = "audio"
os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "")  # e.g., https://<your-subdomain>.ngrok-free.app
TWILIO_CLIENT = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
USE_SIMPLE_TTS = os.getenv("USE_SIMPLE_TTS", "true").lower() in ("1", "true", "yes")
DELIVER_MEDIA_ASYNC = True

def build_public_url_from_base(base: str, path_segment: str):
    base_clean = (base or "").strip()
    if base_clean and not base_clean.endswith('/'):
        base_clean += '/'
    return base_clean + path_segment.lstrip('/')

def set_state(user_id: str, state: str):
    user_states[user_id] = state

def get_state(user_id: str):
    return user_states.get(user_id, "idle")

def clear_state(user_id: str):
    if user_id in user_states:
        del user_states[user_id]

def normalize(text: str):
    return (text or "").strip().lower()


def sanitize_filename(name):
    """Return a filesystem-safe filename (no path components)."""
    # Replace path separators and disallowed characters
    invalid_chars = ['\\', '/', ':', '*', '?', '"', '<', '>', '|']
    sanitized = name
    for ch in invalid_chars:
        sanitized = sanitized.replace(ch, '_')
    # Also replace spaces with underscores for consistency
    sanitized = sanitized.replace(' ', '_').replace('+', '_')
    return os.path.basename(sanitized)

def unique_audio_basename(identifier, kind):
    """Create a unique mp3 file basename for a given user identifier and kind."""
    safe_id = sanitize_filename(identifier or "unknown")
    timestamp_ms = int(time.time() * 1000)
    rand_suffix = os.urandom(3).hex()
    return f"{safe_id}_{kind}_{timestamp_ms}_{rand_suffix}.mp3"

def is_publicly_reachable(url: str):
    return True

def send_whatsapp_media(to_number: str, media_url: str, body: str = None):
    try:
        msg = TWILIO_CLIENT.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            to=to_number,
            body=body,
            media_url=[media_url]
        )
        logging.info(f"Queued WhatsApp media message sid={msg.sid} to={to_number}")
        return True
    except Exception as e:
        logging.error(f"Failed to send WhatsApp media: {e}")
        return False

def _send_media_background(to_number: str, media_path_or_url: str, body: str = None, precomputed_base_url: str = ""):
    try:
        # If we got a local path, convert to public URL
        media = media_path_or_url
        if isinstance(media_path_or_url, str) and not (media_path_or_url.startswith("http://") or media_path_or_url.startswith("https://")):
            # No request context here; use precomputed base URL
            media = build_public_url_from_base(precomputed_base_url, f"audio/{os.path.basename(media_path_or_url)}")
        send_whatsapp_media(to_number, media, body)
    except Exception as e:
        logging.error(f"Background media send failed: {e}")

# -----------------------------
# AssemblyAI STT
# -----------------------------
def transcribe_with_assemblyai(audio_url):
    """Download Twilio audio, upload to AssemblyAI, and get transcription."""
    local_file = "temp_audio.mp3"
    try:
        logging.info(f"Downloading audio from Twilio: {audio_url}")
        response = requests.get(audio_url, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
        if response.status_code != 200:
            logging.error(f"Failed to download Twilio audio: {response.text}")
            return None

        content_type = response.headers.get("Content-Type", "")
        ext = ".mp3"
        if "ogg" in content_type:
            ext = ".ogg"
        elif "mpeg" in content_type or "mp3" in content_type:
            ext = ".mp3"
        elif "wav" in content_type:
            ext = ".wav"

        local_file = f"temp_audio{ext}"
        audio_bytes = response.content
        logging.debug(f"Twilio media Content-Type={content_type}, bytes={len(audio_bytes)}")

        with open(local_file, "wb") as f:
            f.write(audio_bytes)

        # Validate we actually downloaded audio bytes; empty uploads can cause 422
        try:
            downloaded_size_bytes = os.path.getsize(local_file)
        except OSError:
            downloaded_size_bytes = 0
        if downloaded_size_bytes == 0:
            logging.error("Downloaded audio file is empty; aborting transcription to avoid 422 upload error")
            return None

        logging.info("Uploading audio to AssemblyAI...")
        def _chunked_reader(path, chunk_size=5 * 1024 * 1024):
            with open(path, "rb") as fh:
                while True:
                    data = fh.read(chunk_size)
                    if not data:
                        break
                    yield data

        # First attempt: standard upload (set explicit octet-stream content type)
        with open(local_file, "rb") as fbin:
            upload_response = requests.post(
                f"{ASSEMBLYAI_BASE_URL}/upload",
                headers={
                    "authorization": ASSEMBLYAI_API_KEY,
                    "content-type": "application/octet-stream"
                },
                data=fbin
            )

        # Retry with chunked transfer if 422 or non-200
        if upload_response.status_code != 200:
            logging.warning(
                f"Upload attempt 1 failed ({upload_response.status_code}): {upload_response.text}. Retrying chunked..."
            )
            upload_response = requests.post(
                f"{ASSEMBLYAI_BASE_URL}/upload",
                headers={
                    "authorization": ASSEMBLYAI_API_KEY,
                    "content-type": "application/octet-stream"
                },
                data=_chunked_reader(local_file)
            )

        if upload_response.status_code != 200:
            logging.error(f"Upload failed ({upload_response.status_code}): {upload_response.text}")
            return None

        uploaded_url = upload_response.json().get("upload_url")
        data = {"audio_url": uploaded_url, "speech_model": "universal"}
        transcript_response = requests.post(
            f"{ASSEMBLYAI_BASE_URL}/transcript",
            json=data,
            headers={"authorization": ASSEMBLYAI_API_KEY}
        )
        transcript_id = transcript_response.json().get("id")
        polling_endpoint = f"{ASSEMBLYAI_BASE_URL}/transcript/{transcript_id}"

        # Poll with a reasonable cap to avoid long loops
        max_wait_seconds = 60
        start_time = time.time()
        while time.time() - start_time < max_wait_seconds:
            result = requests.get(polling_endpoint, headers={"authorization": ASSEMBLYAI_API_KEY}).json()
            if result.get("status") == "completed":
                logging.info(f"AssemblyAI transcription complete: {result.get('text')}")
                return result.get("text")
            if result.get("status") == "error":
                logging.error(f"AssemblyAI transcription error: {result.get('error')}")
                return None
            time.sleep(2)
        logging.error("AssemblyAI transcription timed out")
        return None

    finally:
        if os.path.exists(local_file):
            os.remove(local_file)

# -----------------------------
# AI Response Generation
# -----------------------------
def generate_with_openrouter(messages):
    prompt_text = messages[-1]["content"] if messages else "Hello"
    try:
        completion = GPT_CLIENT.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "http://localhost:5000",
                "X-Title": "WhatsApp GPT Bot"
            },
            model="openai/gpt-oss-20b:free",
            messages=[{"role": "user", "content": prompt_text}]
        )
        return completion.choices[0].message.content
    except Exception as e:
        logging.error(f"OpenRouter GPT error: {e}")
        return None

def generate_with_gemini(messages):
    prompt_text = messages[-1]["content"] if messages else "Hello"
    try:
        response = GEMINI_CLIENT.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_text
        )
        return response.text
    except Exception as e:
        logging.error(f"Gemini API error: {e}")
        return "Sorry, Gemini service is unavailable."

# -----------------------------
# Murf.ai TTS
# -----------------------------
def text_to_speech_murf(text, filename, prefer_url=False):
    """Generate TTS using Murf SDK; save/copy to requested filename and return its path."""
    try:
        if USE_SIMPLE_TTS:
            # Simple, fast TTS using gTTS, saved locally
            safe_name = sanitize_filename(filename)
            target_path = os.path.join(AUDIO_OUTPUT_DIR, safe_name)
            t0 = time.time()
            gTTS(text=text, lang="en").save(target_path)
            logging.info(f"gTTS synthesis took {time.time() - t0:.2f}s -> {target_path}")
            return target_path

        # Cap text to roughly ~20s of speech for faster generation/delivery
        max_chars = 500
        tts_text = text if len(text) <= max_chars else text[:max_chars]
        if len(text) > max_chars:
            logging.warning(f"Murf TTS text exceeded {max_chars} chars; truncating.")

        # Build output path in audio directory with a safe filename
        safe_name = sanitize_filename(filename)
        target_path = os.path.join(AUDIO_OUTPUT_DIR, safe_name)

        # Use Murf SDK to generate speech
        t0 = time.time()
        sdk_response = MURF_SDK_CLIENT.text_to_speech.generate(
            text=tts_text,
            voice_id="ta-IN-iniya",
            style="Narration",
            multi_native_locale="en-IN",
            format="MP3",
            sample_rate=24000.0
        )
        logging.info(f"Murf TTS generation took {time.time() - t0:.2f}s")

        generated_file = getattr(sdk_response, "audio_file", None)
        if not generated_file:
            logging.error("Murf SDK did not return an audio file path")
            return None

        # If we prefer immediate delivery, return the HTTPS Murf URL directly without downloading
        if prefer_url and isinstance(generated_file, str) and (generated_file.startswith("http://") or generated_file.startswith("https://")):
            logging.info("Returning Murf HTTPS audio URL directly to minimize latency")
            return generated_file

        # Download the returned URL to the requested filename if it's a URL
        if target_path and isinstance(generated_file, str):
            if generated_file.startswith("http://") or generated_file.startswith("https://"):
                def _download_with_retries(url, retries=3, timeout=15):
                    last_err = None
                    for attempt in range(1, retries + 1):
                        try:
                            tdl = time.time()
                            r = requests.get(url, stream=True, timeout=timeout)
                            if r.status_code == 200:
                                with open(target_path, "wb") as out:
                                    for chunk in r.iter_content(chunk_size=8192):
                                        if chunk:
                                            out.write(chunk)
                                logging.info(f"Downloaded Murf audio in {time.time() - tdl:.2f}s -> {target_path}")
                                return True
                            last_err = f"status={r.status_code}"
                            logging.warning(f"Attempt {attempt} to download Murf audio failed: {last_err}")
                        except Exception as e:
                            last_err = str(e)
                            logging.warning(f"Attempt {attempt} to download Murf audio errored: {last_err}")
                            time.sleep(min(2 * attempt, 5))
                    logging.error(f"All attempts to download Murf audio failed: {last_err}")
                    return False

                if _download_with_retries(generated_file):
                    return target_path
                # fall through to gTTS fallback below
            else:
                # If SDK returns a local file path, copy to requested filename
                try:
                    with open(generated_file, "rb") as src, open(target_path, "wb") as dst:
                        dst.write(src.read())
                    logging.info(f"Murf TTS generated: {target_path}")
                    return target_path
                except Exception as copy_err:
                    logging.error(f"Failed to copy Murf audio to target filename: {copy_err}")
                    # fall through to gTTS fallback below

        # If we reached here without returning, try a fast local gTTS fallback
        try:
            t_fallback = time.time()
            gTTS(text=text, lang="en").save(target_path)
            logging.info(f"Fallback gTTS synthesis took {time.time() - t_fallback:.2f}s -> {target_path}")
            return target_path
        except Exception as gtts_err:
            logging.error(f"gTTS fallback failed: {gtts_err}")
            return None
    except Exception as e:
        logging.error(f"Murf TTS failed: {e}")
        return None

# -----------------------------
# Flask Routes
# -----------------------------
@app.route("/")
def index():
    return "WhatsApp AI bot with AssemblyAI STT & Murf.ai TTS is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    incoming_msg = request.values.get("Body", "").strip()
    from_number = request.values.get("From", "unknown")
    media_url = request.values.get("MediaUrl0")
    
    resp = MessagingResponse()

    # Greeting
    nmsg = normalize(incoming_msg)
    if nmsg in ("hi", "hello", "hey", "start", "menu", "good morning", "i need help"):
        # Simple flow: greet and immediately start
        greeting = "Hey there! 👋 How are you doing today?"
        conversations[from_number].append({"role": "assistant", "content": greeting})
        resp.message(greeting)
        clear_state(from_number)
        return Response(str(resp), mimetype="application/xml")

    # Voice note handling
    if media_url:
        incoming_msg = transcribe_with_assemblyai(media_url)
        if not incoming_msg:
            resp.message("Sorry, I couldn’t transcribe your voice note. Please try again.")
            return Response(str(resp), mimetype="application/xml")

    # Farewell handling: end chat with a final text greeting, clear state/history
    nmsg = normalize(incoming_msg)
    if any(word in nmsg for word in FAREWELL_WORDS):
        goodbye_text = "Thanks for chatting! Goodbye 👋"
        conversations[from_number].clear()
        clear_state(from_number)
        resp.message(goodbye_text)
        return Response(str(resp), mimetype="application/xml")

    # State machine
    state = get_state(from_number)
    if state == "await_start":
        # No longer waiting for explicit start; proceed as normal chat
        clear_state(from_number)

    if state == "continue":
        if nmsg in CONTINUE_NO:
            resp.message("Thanks for chatting! Have a great day 👋")
            conversations[from_number].clear()
            clear_state(from_number)
            return Response(str(resp), mimetype="application/xml")
        elif nmsg in CONTINUE_YES:
            clear_state(from_number)
        # otherwise, proceed as free text

    conversations[from_number].append({"role": "user", "content": incoming_msg})
    messages = [{"role": "system", "content": BOT_PERSONA}] + list(conversations[from_number])

    assistant_text = (generate_with_openrouter(messages) or generate_with_gemini(messages)) or "Sorry, I'm having trouble answering right now."
    continue_prompt = "\n\nWould you like to continue? (yes/no)"
    if THANK_YOU_SUFFIX not in assistant_text:
        assistant_text = assistant_text + THANK_YOU_SUFFIX
    # Keep a speech-only version without the continue prompt
    speech_text = assistant_text
    # Append continue prompt to the message we send as text
    assistant_text = assistant_text + continue_prompt
    conversations[from_number].append({"role": "assistant", "content": assistant_text})

    audio_basename = unique_audio_basename(from_number, "response")
    # Always synthesize TTS for the main reply (exclude continue prompt)
    def _task(pre_base):
        audio_path = text_to_speech_murf(speech_text, audio_basename)
        if audio_path:
            _send_media_background(from_number, audio_path, precomputed_base_url=pre_base)
    if DELIVER_MEDIA_ASYNC:
        Thread(target=_task, args=(request.host_url,), daemon=True).start()
    else:
        _task(request.host_url)
    set_state(from_number, "continue")

    # Return empty TwiML so Twilio doesn't send a text; audio will arrive separately
    return Response(str(resp), mimetype="application/xml")

@app.route("/audio/<filename>")
def serve_audio(filename):
    safe_name = sanitize_filename(filename)
    # Set mimetype based on extension so WhatsApp/Twilio can fetch/play
    ext = os.path.splitext(safe_name)[1].lower()
    mimetype = "audio/mpeg"
    if ext == ".wav":
        mimetype = "audio/wav"
    elif ext in (".ogg", ".oga"):
        mimetype = "audio/ogg"
    return send_from_directory(AUDIO_OUTPUT_DIR, safe_name, mimetype=mimetype)

# -----------------------------
# Run Server
# -----------------------------
if __name__ == "__main__":
    logging.info("Flask server running on port 5000 with AssemblyAI STT & Murf.ai TTS support...")
    app.run(host="0.0.0.0", port=5000, debug=True)
