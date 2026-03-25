import customtkinter as ctk
import random
import time
import re
import threading
import os
import json
from datetime import datetime

# Optional imports for Transformers
try:
    from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

# --- CONFIG & COLORS ---
HISTORY_FILE = "chat_history.json"
RULES = [
    (r"hello|hi|hey|greetings", ["Hello there!", "Hi! I'm ChatBuddy. How can I help you today?", "Greetings!"]),
    (r"how are you", ["I'm doing great, feeling more premium than ever!", "All systems go! Ready to chat."]),
    (r"what is your name", ["The name's Buddy. Chat Buddy."]),
    (r"time", ["It's currently {time}."]),
    (r"joke", ["Why did the programmer quit? He didn't get arrays."]),
]

BG_MAIN = "#0F1113"
BG_SIDEBAR = "#16181D"
ACCENT = "#D19A66" 
USER_BUBBLE = "#23262D"
BOT_BUBBLE = "#1A1D23"
TEXT_PRIMARY = "#E0E0E0"
TEXT_SECONDARY = "#ABB2BF"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class ChatApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Chat Buddy Pro")
        self.geometry("900x800")
        self.configure(fg_color=BG_MAIN)

        # Data State
        self.sessions = self.load_history()
        self.current_session_id: str = ""
        self.model_loaded = False
        self.pipe = None
        self.model_name = "Qwen/Qwen2.5-0.5B-Instruct"

        # Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- SIDEBAR ---
        self.sidebar = ctk.CTkFrame(self, fg_color=BG_SIDEBAR, width=260, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        
        self.new_chat_btn = ctk.CTkButton(self.sidebar, text="+ New Chat", fg_color=ACCENT, 
                                         hover_color="#B58654", text_color="white",
                                         font=("Inter", 14, "bold"), height=45,
                                         command=self.start_new_chat)
        self.new_chat_btn.pack(padx=20, pady=25, fill="x")

        self.history_label = ctk.CTkLabel(self.sidebar, text="HISTORY", font=("Inter", 11, "bold"), text_color=TEXT_SECONDARY)
        self.history_label.pack(anchor="w", padx=25, pady=(10, 5))

        self.history_frame = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.history_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.history_buttons = {}

        # --- MAIN CHAT AREA ---
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew")
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(1, weight=1)

        # Header
        self.header_frame = ctk.CTkFrame(self.main_container, fg_color=BG_SIDEBAR, height=70, corner_radius=0)
        self.header_frame.grid(row=0, column=0, sticky="ew")
        
        self.header_label = ctk.CTkLabel(self.header_frame, text="Chat Buddy v2.1", 
                                       font=("Outfit", 20, "bold"), text_color=ACCENT)
        self.header_label.pack(side="left", padx=30, pady=20)
        
        self.mode_label = ctk.CTkLabel(self.header_frame, text="EVOLVING...", 
                                      font=("Consolas", 12), text_color="#E5C07B")
        self.mode_label.pack(side="right", padx=30, pady=20)

        # Chat Bubbles Area
        self.chat_frame = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent", corner_radius=0)
        self.chat_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        # Status & Input
        self.footer = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.footer.grid(row=2, column=0, sticky="ew")
        
        self.status_label = ctk.CTkLabel(self.footer, text="", font=("Inter", 12), text_color=TEXT_SECONDARY)
        self.status_label.pack(anchor="w", padx=35, pady=(5, 0))

        self.input_frame = ctk.CTkFrame(self.footer, fg_color="transparent")
        self.input_frame.pack(fill="x", padx=25, pady=(0, 30))
        self.input_frame.grid_columnconfigure(0, weight=1)

        self.entry = ctk.CTkEntry(self.input_frame, placeholder_text="Ask me anything...",
                                 height=55, corner_radius=28, border_width=1,
                                 fg_color=BOT_BUBBLE, border_color="#2D3139",
                                 text_color=TEXT_PRIMARY, font=("Inter", 15))
        self.entry.grid(row=0, column=0, sticky="ew", padx=(0, 15))
        self.entry.bind("<Return>", self.handle_send)

        self.send_button = ctk.CTkButton(self.input_frame, text="✦", width=55, height=55,
                                        corner_radius=28, fg_color=ACCENT, hover_color="#B58654",
                                        text_color="white", font=("Inter", 20, "bold"),
                                        command=self.handle_send)
        self.send_button.grid(row=0, column=1)

        # Initialisation
        self.refresh_history_ui()
        threading.Thread(target=self.load_model, daemon=True).start()
        
        # Start with a new chat if no history, else load last
        if self.sessions:
            last_id = list(self.sessions.keys())[0]
            self.load_session(last_id)
        else:
            self.start_new_chat()

        # Show Login Screen Overlay
        self.show_login_screen()

    def show_login_screen(self):
        self.login_overlay = ctk.CTkFrame(self, fg_color=BG_MAIN)
        self.login_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        # Center Box
        box = ctk.CTkFrame(self.login_overlay, fg_color=BG_SIDEBAR, width=350, height=450, corner_radius=20)
        box.place(relx=0.5, rely=0.5, anchor="center")
        
        ctk.CTkLabel(box, text="WELCOME BACK", font=("Outfit", 24, "bold"), text_color=ACCENT).pack(pady=(40, 10))
        ctk.CTkLabel(box, text="Please enter your credentials", font=("Inter", 12), text_color=TEXT_SECONDARY).pack(pady=(0, 30))
        
        self.user_entry = ctk.CTkEntry(box, placeholder_text="Username", width=250, height=45, corner_radius=10, border_color="#2D3139")
        self.user_entry.pack(pady=10)
        
        self.pass_entry = ctk.CTkEntry(box, placeholder_text="Password", show="*", width=250, height=45, corner_radius=10, border_color="#2D3139")
        self.pass_entry.pack(pady=10)
        self.pass_entry.bind("<Return>", lambda e: self.attempt_login())
        
        self.login_err_label = ctk.CTkLabel(box, text="", font=("Inter", 11), text_color="#E06C75")
        self.login_err_label.pack(pady=5)
        
        ctk.CTkButton(box, text="Login", fg_color=ACCENT, hover_color="#B58654", 
                      width=250, height=45, corner_radius=10, font=("Inter", 14, "bold"),
                      command=self.attempt_login).pack(pady=20)
        
        forgot_btn = ctk.CTkButton(box, text="Forgot Password?", fg_color="transparent", 
                                   text_color=TEXT_SECONDARY, hover=False, font=("Inter", 12),
                                   command=self.show_password_hint)
        forgot_btn.pack(pady=(0, 20))

    def attempt_login(self):
        username = self.user_entry.get()
        password = self.pass_entry.get()
        
        if username == "chatbuddy" and password == "chatbuddy@123":
            self.login_overlay.destroy()
            self.update_status("READY", "#98C379")
        else:
            self.login_err_label.configure(text="Invalid credentials. Try again.")

    def show_password_hint(self):
        self.login_err_label.configure(text="Hint: chatbuddy / chatbuddy@123", text_color=ACCENT)

    # --- PERSISTENCE ---
    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r") as f:
                    return json.load(f)
            except: return {}
        return {}

    def save_history(self):
        with open(HISTORY_FILE, "w") as f:
            json.dump(self.sessions, f, indent=4)

    # --- SESSION MANAGEMENT ---
    def start_new_chat(self):
        session_id = str(int(time.time()))
        self.sessions[session_id] = {"title": "New Conversation", "messages": []}
        self.current_session_id = session_id
        self.clear_chat_ui()
        self.display_message("Chat Buddy", "How can I help you today?")
        self.refresh_history_ui()

    def load_session(self, session_id):
        self.current_session_id = session_id
        self.clear_chat_ui()
        for msg in self.sessions[session_id]["messages"]:
            self.display_message(msg["role"], msg["content"], save=False)
        self.refresh_history_ui()

    def clear_chat_ui(self):
        for widget in self.chat_frame.winfo_children():
            widget.destroy()

    def refresh_history_ui(self):
        for btn in self.history_buttons.values(): btn.destroy()
        self.history_buttons = {}
        
        # Sort by latest
        sorted_ids = sorted(self.sessions.keys(), reverse=True)
        for sid in sorted_ids:
            title = self.sessions[sid]["title"]
            if len(title) > 25: title = title[:22] + "..."
            
            is_active = sid == self.current_session_id
            bg_color = "#23262D" if is_active else "transparent"
            
            btn = ctk.CTkButton(self.history_frame, text=title, anchor="w",
                               fg_color=bg_color, hover_color="#1F2228",
                               text_color=TEXT_PRIMARY if is_active else TEXT_SECONDARY,
                               font=("Inter", 12), height=40,
                               command=lambda s=sid: self.load_session(s))
            btn.pack(fill="x", pady=2)
            self.history_buttons[sid] = btn

    # --- AI LOGIC ---
    def load_model(self):
        if not TRANSFORMERS_AVAILABLE:
            self.after(0, lambda: self.update_status("SYNC ERROR", "#E06C75"))
            return
        try:
            self.after(0, lambda: self.status_label.configure(text="Initialising AI Model..."))
            dtype = torch.float16 if torch.cuda.is_available() else torch.float32
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self.pipe = pipeline("text-generation", model=self.model_name, torch_dtype=dtype, device=device)
            self.model_loaded = True
            self.after(0, self.on_model_loaded)
        except Exception as e:
            self.after(0, lambda: self.update_status("OFFLINE", "#E06C75"))

    def on_model_loaded(self):
        self.update_status("READY", "#98C379")
        self.status_label.configure(text="")

    def update_status(self, text, color):
        self.mode_label.configure(text=text, text_color=color)

    def handle_send(self, event=None):
        user_input = self.entry.get().strip()
        if not user_input: return
        
        # Update title if it's the first message
        if self.sessions[self.current_session_id]["title"] == "New Conversation":
            self.sessions[self.current_session_id]["title"] = user_input[:30]
            self.refresh_history_ui()
            
        self.display_message("You", user_input)
        self.entry.delete(0, 'end')
        threading.Thread(target=self.process_response, args=(user_input,), daemon=True).start()

    def process_response(self, user_input):
        self.after(0, lambda: self.status_label.configure(text="Buddy is thinking..."))
        response = self.generate_response(user_input)
        self.after(0, self.finish_response, response)

    def finish_response(self, response):
        self.status_label.configure(text="")
        self.display_message("Chat Buddy", response)

    def generate_response(self, user_input):
        if self.model_loaded and self.pipe:
            try:
                prompt = f"<|im_start|>system\nYou are a helpful and friendly chatbot named Chat Buddy.<|im_end|>\n<|im_start|>user\n{user_input}<|im_end|>\n<|im_start|>assistant\n"
                outputs = self.pipe(prompt, max_new_tokens=200, do_sample=True, temperature=0.7)
                full_text = outputs[0]["generated_text"]
                if "<|im_start|>assistant\n" in full_text:
                    response = full_text.split("<|im_start|>assistant\n")[-1].split("<|im_end|>")[0].strip()
                else: response = full_text.replace(prompt, "").strip()
                return response
            except: pass

        clean_input = user_input.lower()
        for pattern, responses in RULES:
            if re.search(pattern, clean_input):
                resp = random.choice(responses)
                if "{time}" in resp: resp = resp.replace("{time}", time.strftime('%I:%M %p'))
                return resp
        return "I'm currently in offline mode. Sync complete soon!"

    def display_message(self, sender, message, save=True):
        if save and self.current_session_id:
            self.sessions[self.current_session_id]["messages"].append({"role": sender, "content": message})
            self.save_history()
            
        is_user = sender == "You"
        bubble_color = USER_BUBBLE if is_user else BOT_BUBBLE
        align = "e" if is_user else "w"
        padx = (80, 20) if is_user else (20, 80)
        
        bubble_frame = ctk.CTkFrame(self.chat_frame, fg_color=bubble_color, corner_radius=18)
        bubble_frame.pack(anchor=align, padx=padx, pady=8)
        
        msg_label = ctk.CTkLabel(bubble_frame, text=message, font=("Inter", 14), 
                                text_color=TEXT_PRIMARY, wraplength=450, justify="left")
        msg_label.pack(padx=20, pady=12)
        self.after(100, self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        try:
            # CTkScrollableFrame internal canvas access
            self.chat_frame._parent_canvas.yview_moveto(1.0)
        except:
            pass

if __name__ == "__main__":
    app = ChatApp()
    app.mainloop()
