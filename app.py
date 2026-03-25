import os
import json
import time
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
import threading

# Optional imports
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    from transformers import pipeline
    import torch
    TRANSFORMERS_AVAILABLE = True
except (ImportError, RuntimeError):
    # RuntimeError can happen if torch is partially installed or lacks dependencies on serverless
    TRANSFORMERS_AVAILABLE = False

app = Flask(__name__)
CORS(app)
app.secret_key = "supersecretkeyforchatbuddy"

HISTORY_FILE = "chat_history.json"
CONFIG_FILE = "config.json"
MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"

# Global AI Pipeline (Lazy Load)
ai_pipe = None
model_loaded = False
gemini_model = None

def load_ai():
    global ai_pipe, model_loaded, gemini_model
    
    # 1. Try Gemini (Cloud / Vercel)
    api_key = os.getenv("GOOGLE_API_KEY")
    if GEMINI_AVAILABLE and api_key:
        try:
            genai.configure(api_key=api_key)
            gemini_model = genai.GenerativeModel('gemini-1.5-flash')
            model_loaded = True
            print("Gemini Cloud AI loaded.")
            return
        except Exception as e:
            print(f"Gemini Init Error: {e}")

    # 2. Fallback to Local (Desktop)
    if TRANSFORMERS_AVAILABLE:
        try:
            dtype = torch.float16 if torch.cuda.is_available() else torch.float32
            device = "cuda" if torch.cuda.is_available() else "cpu"
            ai_pipe = pipeline("text-generation", model=MODEL_NAME, torch_dtype=dtype, device=device)
            model_loaded = True
            print("Local AI Model loaded.")
        except Exception as e:
            print(f"Local AI Init Error: {e}")

# Start loading in background
threading.Thread(target=load_ai, daemon=True).start()

# --- HELPERS ---
def get_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except: pass
    return {"username": "chatbuddy", "password": "chatbuddy@123"}

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def get_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except: return {}
    return {}

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)

# --- ROUTES ---
@app.route('/')
def home():
    if 'user' not in session:
        return render_template('login.html')
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    config = get_config()
    if username == config["username"] and password == config["password"]:
        session['user'] = username
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Invalid credentials"}), 401

@app.route('/logout')
def logout():
    session.pop('user', None)
    return jsonify({"success": True})

@app.route('/api/history', methods=['GET'])
def fetch_history():
    return jsonify(get_history())

@app.route('/api/settings', methods=['POST'])
def update_settings():
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    config = get_config()
    config["username"] = data.get('username', config["username"])
    config["password"] = data.get('password', config["password"])
    save_config(config)
    return jsonify({"success": True})

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_input = data.get('message')
    session_id = data.get('session_id')
    
    if not user_input or not session_id:
        return jsonify({"error": "Missing data"}), 400
    
    history = get_history()
    if session_id not in history:
        history[session_id] = {"title": user_input[:30], "messages": []}
    
    # AI Response
    response = generate_ai_response(user_input)
    
    # Save to history
    history[session_id]["messages"].append({"role": "You", "content": user_input})
    history[session_id]["messages"].append({"role": "Chat Buddy", "content": response})
    save_history(history)
    
    return jsonify({"response": response, "session_id": session_id, "title": history[session_id]["title"]})

def generate_ai_response(user_input):
    if not model_loaded:
        return "Thinking... (Initialising Brain)"
    
    # Try Gemini first
    if gemini_model:
        try:
            response = gemini_model.generate_content(user_input)
            return response.text
        except Exception as e:
            print(f"Gemini error: {e}")

    # Fallback to Local AI
    if ai_pipe:
        try:
            prompt = f"<|im_start|>system\nYou are a helpful and friendly chatbot named Chat Buddy.<|im_end|>\n<|im_start|>user\n{user_input}<|im_end|>\n<|im_start|>assistant\n"
            outputs = ai_pipe(prompt, max_new_tokens=200, do_sample=True, temperature=0.7)
            full_text = outputs[0]["generated_text"]
            if "<|im_start|>assistant\n" in full_text:
                return full_text.split("<|im_start|>assistant\n")[-1].split("<|im_end|>")[0].strip()
            return full_text.replace(prompt, "").strip()
        except: pass
    
    return "I'm currently thinking... try again in a moment."

if __name__ == '__main__':
    # Flask runs on 5000 by default
    app.run(debug=True, port=5000)
