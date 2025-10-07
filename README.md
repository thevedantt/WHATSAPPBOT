# 💬 WhatsApp GPT Bot (Twilio)

A **minimal AI-powered WhatsApp chatbot** built using **Flask** and **Twilio**, designed to provide seamless, intelligent, and conversational experiences.  
It generates **AI-based text responses** and can optionally deliver **text-to-speech (TTS) audio messages** asynchronously.  
This project is optimized for quick demonstrations and fulfills the AI Internship assignment requirements. ⚙️  

---

## 🧠 About the Project  

The WhatsApp GPT Bot enables users to interact naturally through WhatsApp using AI-generated responses.  
It integrates GPT via **OpenRouter API**, with a **Google Gemini fallback** to ensure uninterrupted replies even during API failures or rate limits.  
Additionally, it supports optional **voice messages** using **Murf SDK** and **gTTS**, making the experience more dynamic and human-like. 🎧  

---

## 🌟 Features  

- 🤖 **Greeting on First Contact** — The bot warmly welcomes the user upon their first message.  
- 💬 **Free-text Conversation with AI** — Powered by **OpenRouter** for GPT-style responses with a **Gemini fallback** for reliability.  
- 🔊 **TTS Audio Reply (Murf SDK → gTTS Fallback)** — Converts responses into speech and sends them asynchronously as a second message.  
- 🔁 **“Continue? (yes/no)” Loop** — After each response, the bot asks if the user wants to continue chatting, skipping audio for this prompt.  

---

## 🧩 Prerequisites  

- 🐍 Python 3.10+  
- 📱 Twilio WhatsApp Sandbox or Approved Business Sender  
- 🌐 ngrok (or any public HTTPS tunneling service)  

---

## ⚙️ Setup Instructions  

1️⃣ **Install Dependencies**  
```bash
pip install -r requirements.txt
```

2️⃣ **Configure Environment Variables** (Windows PowerShell Example)  
```powershell
setx TWILIO_ACCOUNT_SID "<your_sid>"
setx TWILIO_AUTH_TOKEN "<your_auth_token>"
setx PUBLIC_BASE_URL "https://<your-ngrok-subdomain>.ngrok-free.app"
```

👉 Optional: Enable simple TTS fallback  
```powershell
setx USE_SIMPLE_TTS "true"  # uses gTTS locally
```

3️⃣ **Start the Flask Server**  
```bash
python app.py
```

4️⃣ **Expose Server via ngrok** (or use the provided script)  
```powershell
powershell -ExecutionPolicy Bypass -File .\ngrok-setup.ps1
```

5️⃣ **Set Twilio WhatsApp Webhook**  
- When a new ngrok URL is displayed, update your Twilio Sandbox webhook:  
  - **When a message comes in:** `https://<your-ngrok>/webhook`  

---

## 💬 Usage  

- Send a message like **“hi”** or **“hello”** to your WhatsApp sandbox number.  
- You’ll receive a friendly greeting — “Hey there! 👋 How are you doing today?”  
- The bot then offers an option to **Start Chat**.  
- Once started, it replies to all free-text messages with **AI-generated responses**.  
- Finally, it ends with a polite message — “Thank you for chatting with me! 🌟”.  

---

## 🗂️ Notes  

- 🎧 Audio files are generated dynamically in the `/audio/<filename>` directory.  
- ⏩ TTS audio replies are sent asynchronously for smoother user experience.  
- 🔇 No audio is generated for the “continue” prompt.  

---

## 🧱 Repository Info  

- Keep `info.txt` for quick reference.  
- The `ngrok-setup.ps1` script simplifies ngrok authentication and tunnel creation.  
- Clean and minimal structure optimized for demonstration and performance.  

---

## 🧩 Troubleshooting  

- ⚠️ If **OpenRouter** free tier is rate-limited (HTTP 429), the bot automatically switches to **Gemini**.  
- 🔁 If **Murf TTS** fails to generate audio, it falls back to **gTTS**.  
- 🌍 Ensure your `PUBLIC_BASE_URL` points to a valid **HTTPS** address accessible by Twilio.  

---

## 🧰 Tools Used  

- 🧩 **Flask** — Backend framework for handling routes and Twilio webhooks.  
- 💬 **Twilio API** — Enables WhatsApp communication and message automation.  
- 🔗 **ngrok** — Exposes the local Flask server to the internet via secure HTTPS tunneling.  
- 🧠 **OpenRouter API** — Provides GPT-style text generation capabilities.  
- ⚡ **Google Gemini** — Fallback AI model for enhanced reliability.  
- 🎧 **Murf SDK** & **gTTS** — Generate and deliver audio responses.  
- 🧾 **Python-dotenv** — Secure management of environment variables.  
- ⚙️ **PowerShell Scripts** — Simplify ngrok setup and webhook configuration.  

---

## 💡 Additional Insights  

While building this bot, I also explored **Gupshup**, a WhatsApp Business API platform that offers a simpler setup and pre-built templates for quick chatbot deployment.  
However, I selected **Twilio** for its **flexibility, Python compatibility, and better webhook control**.  
Understanding both platforms provided a broader perspective on WhatsApp automation workflows. 🚀  

---

## 🏁 Conclusion  

This project demonstrates effective integration of **AI models**, **real-time API communication**, and **voice automation** — all through a simple WhatsApp interface.  
It showcases **error-handling, fallback strategies, and asynchronous responses**, ensuring reliability even under free-tier limitations.  

**Thank you for reading! 🌟**
