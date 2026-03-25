# ChatBuddy Pro 🚀

ChatBuddy Pro is a premium, local-first AI chatbot application that supports **Desktop**, **Web**, and **Cloud (Vercel)** environments. It features a modern design, persistent chat history, and secure login.

## ✨ Features
- **Local AI Brain**: Optimized with Qwen2.5-0.5B for fast, private inference on your hardware.
- **Premium UI**: Modern dark-mode interfaces built with `customtkinter` (Desktop) and Glassmorphism (Web).
- **Chat History**: Save and manage multiple conversation sessions across all platforms.
- **Cloud Ready**: One-click deployment to Vercel with Gemini 1.5 Flash integration.
- **Secure Entry**: Protected by a customizable login system.

## 🛠️ Versions

### 1. Desktop App (`gui_chatbot.py`)
- Best for full privacy and offline use.
- **Run**: `launch_app.bat`

### 2. Local Web App (`app.py`)
- Best for URL access on your local network.
- **Run**: `launch_web_app.bat`

### 3. Vercel Cloud
- Best for sharing and mobile access.
- Integrated with Gemini API for serverless performance.

## 🚀 Getting Started

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Setup Gemini (Optional for Cloud)**:
   - Add `GOOGLE_API_KEY` to your environment variables for web/cloud features.
3. **Run**:
   - Execute `launch_app.bat` to start the desktop version.

## 📄 License
MIT License. Feel free to use and modify!
