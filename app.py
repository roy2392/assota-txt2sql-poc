from flask import Flask, render_template, request, jsonify
import sqlite3
import google.generativeai as genai
import os
import re
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# הגדרת מפתח API של Gemini
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# זיכרון צ'אט בשרת
chat_sessions = {}

def get_user_data(user_id):
    """שליפת נתוני המשתמש מה־DB"""
    conn = sqlite3.connect('app_database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.*, u.user_name, u.age
        FROM appointments a 
        JOIN accounts u ON a.user_id = u.user_id 
        WHERE a.user_id=?
    """, (user_id,))
    user_data = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return user_data

def find_next_appointment(user_data):
    """איתור התור הקרוב ביותר בעתיד"""
    now = datetime.now()
    next_appointment = None
    for appt in user_data:
        appt_date_str = appt.get('appointment_date_Time__c')
        if not appt_date_str:
            continue
        try:
            appt_date = datetime.strptime(appt_date_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            continue
        if appt_date > now:
            if next_appointment is None:
                next_appointment = appt
            else:
                cur = datetime.strptime(next_appointment.get('appointment_date_Time__c'), '%Y-%m-%d %H:%M:%S')
                if appt_date < cur:
                    next_appointment = appt
    return next_appointment

def format_bot_text(text):
    """המרת טקסט רגיל עם מספור/נקודות ל־HTML <ol>/<ul> עם ניקוי כוכביות"""
    if not text:
        return ""
    if any(tag in text for tag in ("<ol", "<ul", "<li")):
        return text

    # מסירים כוכביות מיותרות מהטקסט
    text = text.replace('*', '')

    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]

    if not lines:
        return ""

    num_re = re.compile(r'^\d+[\.\)]\s+')
    bullet_re = re.compile(r'^([\-•])\s+')

    num_hits = sum(1 for ln in lines if num_re.match(ln))
    bullet_hits = sum(1 for ln in lines if bullet_re.match(ln))

    if num_hits >= max(2, len(lines) // 2):
        items = [num_re.sub('', ln) for ln in lines if num_re.match(ln)]
        if items:
            return "<ol>" + "".join(f"<li>{it}</li>" for it in items) + "</ol>"

    if bullet_hits >= max(2, len(lines) // 2):
        items = [bullet_re.sub('', ln) for ln in lines if bullet_re.match(ln)]
        if items:
            return "<ul>" + "".join(f"<li>{it}</li>" for it in items) + "</ul>"

    return "<br>".join(lines)

    # רשימה עם נקודות
    if bullet_hits >= max(2, len(lines) // 2):
        items = [bullet_re.sub('', ln) for ln in lines if bullet_re.match(ln)]
        if items:
            return "<ul>" + "".join(f"<li>{it}</li>" for it in items) + "</ul>"

    # ברירת מחדל - שבירת שורות
    return "<br>".join(lines)

@app.route('/')
def index():
    """עמוד ראשי"""
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start_chat():
    """תחילת שיחה - בקשת ת"ז"""
    session_id = os.urandom(16).hex()
    chat_sessions[session_id] = {'state': 'waiting_for_id', 'history': []}
    
    response1 = """צהריים טובים! 👋<br>
ברוכה הבאה לצ׳אט של אסותא – אני כאן כדי לעזור לך עם כל מה שקשור לתורים, בדיקות ותוצאות.<br><br>
רוצה לדעת מתי התור הבא שלך? 🗓️<br>
לקבל הנחיות לבדיקה? 📝<br>
לבדוק אם תוצאות המעבדה כבר מוכנות? 🔬<br><br>
פשוט תכתבי לי – ואני אדאג לכל השאר.<br>
שירות מהיר, נעים וללא המתנה לנציג. 💨"""
    
    response2 = 'כדי שנתחיל יש להזין את מספר ת"ז שלך'

    return jsonify({'session_id': session_id, 'responses': [response1, response2]})

@app.route('/chat', methods=['POST'])
def chat():
    """ניהול השיחה"""
    session_id = request.json.get('session_id')
    user_message = request.json.get('message')

    if not session_id or not user_message:
        return jsonify({'error': 'session_id and message are required.'}), 400

    session = chat_sessions.get(session_id)
    if not session:
        return jsonify({'error': 'Invalid session ID.'}), 400

    if session['state'] == 'waiting_for_id':
        user_id = user_message.strip()
        user_data = get_user_data(user_id)
        if not user_data:
            return jsonify({'response': 'לא מצאתי מטופל עם המזהה הזה. אנא נסה שוב.'})

        try:
            with open('system_prompt.txt', 'r', encoding='utf-8') as f:
                system_prompt = f.read()
        except FileNotFoundError:
            return jsonify({'error': 'System prompt file not found.'}), 500

        first_name = user_data[0].get('user_name')
        if first_name:
            greeting = f'שלום {first_name}! אני אסי, עוזר ה־AI החדש של אסותא. איך אני יכול לעזור לך היום?'
        else:
            greeting = 'תודה! איך אני יכול לעזור לך היום?'

        model = genai.GenerativeModel(
            'gemini-1.5-flash',
            system_instruction=system_prompt
        )
        
        session['user_id'] = user_id
        session['state'] = 'chatting'
        session['model'] = model
        session['history'] = [
            {"role": "user", "parts": [f"המשתמש (user_id: {user_id}, age: {user_data[0]['age']}) התחבר. הנה הנתונים שלו: {user_data}"]},
            {"role": "model", "parts": ["שלום! אני הבוט של אסותא. איך אני יכול לעזור?"]}
        ]
        return jsonify({'response': greeting})

    # מצב שיחה פעילה
    if "next appointment" in user_message.lower() or "תור קרוב" in user_message:
        user_data = get_user_data(session['user_id'])
        next_appointment = find_next_appointment(user_data)
        if next_appointment:
            response_text = f"התור הבא שלך הוא ב־{next_appointment['appointment_date_Time__c']} מסוג {next_appointment['appointment_type']}."
        else:
            response_text = "לא מצאתי תורים עתידיים."
    else:
        chat = session["model"].start_chat(history=session["history"])
        response = chat.send_message(user_message)
        session["history"] = chat.history
        response_text = response.text.strip()

    # פורמט אוטומטי לרשימות
    formatted_response = format_bot_text(response_text)
    return jsonify({'response': formatted_response})

if __name__ == '__main__':
    app.run(debug=True)