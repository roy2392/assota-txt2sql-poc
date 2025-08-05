from flask import Flask, render_template, request, jsonify
import sqlite3
import google.generativeai as genai
import os

app = Flask(__name__)

# Configure the Gemini API key
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

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

    prompt = f"המשתמש (user_id: {user_id}) שואל: {user_question}\n\nהנה הנתונים שלו: {user_data}"
    response = model.generate_content(prompt)

    return jsonify({'response': response.text})

if __name__ == '__main__':
    app.run(debug=True)
