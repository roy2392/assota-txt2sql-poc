from flask import Flask, render_template, request, jsonify
import sqlite3
import google.generativeai as genai
import os

app = Flask(__name__)

# Configure the Gemini API key
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# In-memory chat history
chat_sessions = {}

def get_user_data(user_id):
    """Fetches user data from the database."""
    conn = sqlite3.connect('app_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM appointments WHERE user_id=?", (user_id,))
    user_data = cursor.fetchall()
    conn.close()
    return user_data

@app.route('/')
def index():
    """Renders the main chat page."""
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start_chat():
    """Starts a new chat session and asks for user ID."""
    session_id = os.urandom(16).hex()
    chat_sessions[session_id] = {'state': 'waiting_for_id', 'history': []}
    return jsonify({'session_id': session_id, 'response': 'שלום! אני הבוט של אסותא. מה מספר המזהה שלך?'})

@app.route('/chat', methods=['POST'])
def chat():
    """Handles chat messages."""
    session_id = request.json.get('session_id')
    user_message = request.json.get('message')

    if not session_id or not user_message:
        return jsonify({'error': 'session_id and message are required.'}), 400

    session = chat_sessions.get(session_id)
    if not session:
        return jsonify({'error': 'Invalid session ID.'}), 400

    if session['state'] == 'waiting_for_id':
        user_id = user_message
        user_data = get_user_data(user_id)
        if not user_data:
            return jsonify({'response': 'לא מצאתי מטופל עם המזהה הזה. אנא נסה שוב.'})

        try:
            with open('system_prompt.txt', 'r', encoding='utf-8') as f:
                system_prompt = f.read()
        except FileNotFoundError:
            return jsonify({'error': 'System prompt file not found.'}), 500

        model = genai.GenerativeModel(
            'gemini-1.5-flash',
            system_instruction=system_prompt
        )
        
        session['state'] = 'chatting'
        session['model'] = model
        session['history'] = [
            {"role": "user", "parts": [f"המשתמש (user_id: {user_id}) התחבר. הנה הנתונים שלו: {user_data}"]},
            {"role": "model", "parts": ["שלום! אני הבוט של אסותא. איך אני יכול לעזור?"]}
        ]
        return jsonify({'response': 'תודה! איך אני יכול לעזור לך היום?'})

    elif session['state'] == 'chatting':
        chat = session["model"].start_chat(history=session["history"])
        response = chat.send_message(user_message)
        session["history"] = chat.history
        return jsonify({'response': response.text})

if __name__ == '__main__':
    app.run(debug=True)
