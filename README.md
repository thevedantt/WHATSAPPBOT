.

💬 WhatsApp GPT Bot (Twilio)

A minimal AI-powered WhatsApp chatbot built using Flask and Twilio, designed to provide seamless and intelligent chat experiences. It generates AI-based text responses and can optionally deliver text-to-speech (TTS) audio messages asynchronously. This setup is optimized for quick demonstrations and assignment submissions. ⚙️

🌟 Features

🤖 Greeting on First Contact — The bot warmly welcomes the user upon initial interaction.

💬 Free-text Conversation with AI — Powered by OpenRouter for GPT-style responses, with an automatic Gemini fallback to ensure reliability.

🔊 TTS Audio Reply (Murf SDK → gTTS Fallback) — Converts text responses into speech and sends them as a second asynchronous message for a richer user experience.

🔁 “Continue? (yes/no)” Loop — After each reply, the bot checks if the user wishes to continue the conversation, skipping audio generation for this prompt.

🧩 Prerequisites

🐍 Python 3.10+

📱 Twilio WhatsApp Sandbox or Approved Sender

🌐 ngrok (or any public HTTPS tunneling service)

⚙️ Setup Instructions

1️⃣ Install Dependencies

pip install -r requirements.txt


2️⃣ Configure Environment Variables (Windows PowerShell Example)

setx TWILIO_ACCOUNT_SID "<your_sid>"
setx TWILIO_AUTH_TOKEN "<your_auth_token>"
setx PUBLIC_BASE_URL "https://<your-ngrok-subdomain>.ngrok-free.app"


👉 Optional: Enable simple TTS fallback

setx USE_SIMPLE_TTS "true"  # uses gTTS locally


3️⃣ Start the Flask Server

python app.py


4️⃣ Expose Server via ngrok (or use the provided script)

powershell -ExecutionPolicy Bypass -File .\ngrok-setup.ps1


5️⃣ Set Twilio WhatsApp Webhook

When a new ngrok URL is displayed, update your Twilio Sandbox webhook:

When a message comes in: https://<your-ngrok>/webhook

💬 Usage

Send a simple “hi” or “hello” to your WhatsApp sandbox number.

Receive a friendly greeting and start chatting freely.

After each AI response, the bot will ask “Continue? (yes/no)” — reply accordingly.

🗂️ Notes

🎧 Audio files are stored in /audio/<filename> and generated dynamically.

⏩ For efficiency, TTS audio messages are sent asynchronously as a second message.

🔇 No audio is generated for the continue prompt.

🧱 Repository Info

Keep info.txt for quick reference.

Development scripts include ngrok-setup.ps1 for rapid ngrok configuration and authentication.

🧩 Troubleshooting

⚠️ If OpenRouter free tier is rate-limited (HTTP 429), the bot automatically falls back to Gemini.

🔁 If Murf TTS fails to download, it reverts to gTTS for speech generation.

🌍 Ensure your PUBLIC_BASE_URL is a valid HTTPS URL accessible by Twilio for media delivery.

🧰 Tools Used

🧩 Flask — For backend server and webhook handling.

💬 Twilio API — For WhatsApp message exchange and automation.

🔗 ngrok — For tunneling localhost to public HTTPS endpoints.

🧠 OpenRouter API — For GPT-style text generation.

⚡ Google Gemini — As an intelligent fallback model for continuity.

🎧 Murf SDK & gTTS — For text-to-speech (TTS) audio generation.

🧾 Python-dotenv — For secure environment variable management.

⚙️ PowerShell Scripts — For quick ngrok setup and configuration.
