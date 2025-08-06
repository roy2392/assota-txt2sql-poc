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

@app.route('/chat', methods=['POST'])
def chat():
    """Handles chat messages."""
    user_id = request.json.get('user_id')
    user_question = request.json.get('message')

    if not user_id or not user_question:
        return jsonify({'error': 'user_id and message are required.'}), 400

    # Initialize chat history if it's a new session
    if user_id not in chat_sessions:
        user_data = get_user_data(user_id)
        if not user_data:
            return jsonify({'response': 'לא מצאתי מטופל עם המזהה הזה.'})
        
        try:
            with open('system_prompt.txt', 'r', encoding='utf-8') as f:
                system_prompt = f.read()
        except FileNotFoundError:
            return jsonify({'error': 'System prompt file not found.'}), 500

        model = genai.GenerativeModel(
            'gemini-1.5-flash',
            system_instruction=system_prompt
        )
        
        # Store the model and history in the session
        chat_sessions[user_id] = {
            "model": model,
            "history": [
                {
                    "role": "user",
                    "parts": [f"המשתמש (user_id: {user_id}) התחבר. הנה הנתונים שלו: {user_data}"],
                },
                {
                    "role": "model",
                    "parts": ["שלום! אני הבוט של אסותא. איך אני יכול לעזור?"],
                }
            ]
        }

    # Get the chat session
    session = chat_sessions[user_id]
    chat = session["model"].start_chat(history=session["history"])
    
    # Send the new message and get the response
    response = chat.send_message(user_question)
    
    # Update the history
    session["history"] = chat.history

    return jsonify({'response': response.text})

if __name__ == '__main__':
    app.run(debug=True)
