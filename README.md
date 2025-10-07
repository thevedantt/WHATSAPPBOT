# WhatsApp GPT Bot (Twilio)

A minimal WhatsApp chatbot using Flask + Twilio. It replies with AI-generated text and can send TTS audio asynchronously. Optimized for quick demo and assignment requirements.

## Features
- Greeting on first contact
- Free-text conversation with AI (OpenRouter → Gemini fallback)
- **TTS audio reply** (Murf SDK → gTTS fallback), sent as a second message
- **"Continue? (yes/no)" loop** after each reply; skipping audio for that prompt

## Prerequisites
- Python 3.10+
- Twilio WhatsApp sandbox or approved sender
- ngrok (or public HTTPS)

## Setup
1) Install deps
```bash
pip install -r requirements.txt
```

2) Configure environment (Windows PowerShell example)
```powershell
setx TWILIO_ACCOUNT_SID "<your_sid>"
setx TWILIO_AUTH_TOKEN "<your_auth_token>"
setx PUBLIC_BASE_URL "https://<your-ngrok-subdomain>.ngrok-free.app"
```
Optionally toggle simple TTS fallback:
```powershell
setx USE_SIMPLE_TTS "true"  # uses gTTS locally
```

3) Start server
```bash
python app.py
```

4) Expose via ngrok (or use the provided script)
```powershell
powershell -ExecutionPolicy Bypass -File .\ngrok-setup.ps1
```

5) Set Twilio WhatsApp webhook
- When a new ngrok URL is shown, set your Twilio WhatsApp sandbox/webhook:
  - When a message comes in: `https://<your-ngrok>/webhook`

## Usage
- Send "hi" or "hello" to your WhatsApp sandbox number.
- You’ll get a greeting. Type anything to chat.
- After each answer, bot asks if you want to continue; reply yes/no.

## Notes
- Audio files are served from `/audio/<filename>` and generated into the `audio/` folder.
- For speed, TTS audio is sent in a second, asynchronous message.
- Audio is not generated for the "continue" prompt.

## Repository
- Keep `info.txt` for quick reference; other dev artifacts were removed during cleanup.
- Scripts: `ngrok-setup.ps1` for quick ngrok auth and tunnel.

## Troubleshooting
- If OpenRouter free tier is rate-limited (429), the app falls back to Gemini.
- If Murf TTS download fails, the app falls back to gTTS.
- If audio links fail to deliver, ensure `PUBLIC_BASE_URL` is set to an HTTPS URL reachable by Twilio.
