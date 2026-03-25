let currentSessionId = "";
let sessions = {};

async function loadInitialData() {
    const res = await fetch('/api/history');
    sessions = await res.json();
    renderHistory();
    
    // Load last session if available
    const sessionIds = Object.keys(sessions).sort().reverse();
    if (sessionIds.length > 0) {
        loadSession(sessionIds[0]);
    } else {
        startNewChat();
    }
}

function renderHistory() {
    const list = document.getElementById('history-list');
    list.innerHTML = "";
    
    Object.keys(sessions).sort().reverse().forEach(id => {
        const div = document.createElement('div');
        div.className = `history-item ${id === currentSessionId ? 'active' : ''}`;
        div.innerText = sessions[id].title || "New Conversation";
        div.onclick = () => loadSession(id);
        list.appendChild(div);
    });
}

function loadSession(id) {
    currentSessionId = id;
    const container = document.getElementById('messages');
    container.innerHTML = "";
    
    sessions[id].messages.forEach(msg => {
        appendMessage(msg.role === "You" ? "user" : "bot", msg.content);
    });
    
    renderHistory();
}

function startNewChat() {
    currentSessionId = Date.now().toString();
    sessions[currentSessionId] = { title: "New Conversation", messages: [] };
    const container = document.getElementById('messages');
    container.innerHTML = "";
    appendMessage("bot", "Welcome back! I'm ready to assist.");
    renderHistory();
}

function appendMessage(type, content) {
    const container = document.getElementById('messages');
    const div = document.createElement('div');
    div.className = `chat-bubble ${type}`;
    div.innerText = content;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

async function sendMessage() {
    const input = document.getElementById('user-input');
    const msg = input.value.trim();
    if (!msg) return;

    input.value = "";
    appendMessage("user", msg);
    
    document.getElementById('typing-status').innerText = "Buddy is thinking...";

    try {
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: msg, session_id: currentSessionId })
        });
        
        const data = await res.json();
        document.getElementById('typing-status').innerText = "";
        
        // Update local session data
        if (!sessions[data.session_id]) {
            sessions[data.session_id] = { title: data.title, messages: [] };
        }
        sessions[data.session_id].title = data.title;
        sessions[data.session_id].messages.push({ role: "You", content: msg });
        sessions[data.session_id].messages.push({ role: "Chat Buddy", content: data.response });
        
        appendMessage("bot", data.response);
        renderHistory();
    } catch (err) {
        document.getElementById('typing-status').innerText = "Sync Error.";
    }
}

function handleKeyPress(e) {
    if (e.key === 'Enter') sendMessage();
}

// Start
loadInitialData();
