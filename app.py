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

def should_add_followup_question(user_message, response_text):
    """קובע אם צריך להוסיף שאלת המשך לתשובה"""
    appointment_keywords = ['תור', 'תורים', 'בדיקה', 'בדיקות', 'appointment', 'המטולוג', 'עיניים', 'גסטרו', 'CT', 'MRI']
    user_lower = user_message.lower()
    response_lower = response_text.lower()
    
    # בדיקה אם השאלה או התשובה קשורות לתורים
    user_has_appointment = any(keyword in user_lower for keyword in appointment_keywords)
    response_has_appointment = any(keyword in response_lower for keyword in appointment_keywords)
    
    # לא מוסיפים שאלת המשך אם המשתמש כבר שאל שאלה ספציפית
    specific_questions = ['איך', 'מה', 'מתי', 'איפה', 'כמה', 'האם', 'הגעה', 'להביא', 'צום', 'הכנה']
    user_asked_specific = any(q in user_lower for q in specific_questions)
    
    return (user_has_appointment or response_has_appointment) and not user_asked_specific

def generate_followup_question(user_message, response_text):
    """יוצר שאלת המשך מתאימה בהתבסס על התשובה"""
    user_lower = user_message.lower()
    response_lower = response_text.lower()
    
    # שאלות המשך בהתבסס על סוג התשובה
    if 'תורים' in response_lower or 'תור' in response_lower:
        # If response lists multiple appointments
        if 'מצאתי' in response_lower and ('1.' in response_text or 'רופא' in response_text):
            return "האם תרצה פרטים נוספים על אחד מהתורים? 📝"
        # If it's a single appointment with details
        elif any(word in response_lower for word in ['המטולוג', 'עיניים', 'שינה', 'ct', 'mri', 'בדיקת']):
            return "האם תרצה לדעת מה להביא לבדיקה או איך להגיע? 📋"
        # If user asked about next appointment specifically
        elif 'תור הבא' in user_lower or 'תור קרוב' in user_lower:
            return "יש לך שאלות על ההכנות לבדיקה או הנחיות הגעה? 🗺️"
    
    # If no appointments found
    if 'לא מצאתי תורים' in response_lower:
        return "האם תרצה לקבוע תור חדש או לבדוק תורים בתאריך אחר? 📅"
    
    # If response contains appointment details/instructions
    if any(word in response_lower for word in ['הצטייד', 'להביא', 'הכנה', 'הנחיות', 'צום']):
        return "יש לך עוד שאלות על הבדיקה? 🤔"
    
    return None

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
 אני אסי, עוזר הבינה המלאכותית של אסותא 🤖. כאן כדי לעזור לך עם כל מה שקשור לתורים, בדיקות ותוצאות.<br><br>
רוצה לדעת מתי התור הבא שלך? 🗓️<br>
לקבל הנחיות לבדיקה? 📝<br>
לבדוק אם תוצאות המעבדה כבר מוכנות? 🔬<br><br>
פשוט תכתוב לי – ואני אדאג לכל השאר.<br>
שירות מהיר, נעים וללא המתנה לנציג. ✨"""
    
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
    
    # Debug: Print session info
    print(f"Debug - Session ID: {session_id}")
    print(f"Debug - Session keys: {session.keys()}")
    print(f"Debug - Current state: {session.get('state')}")

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
            greeting = f'שלום {first_name}! איך אוכל לעזור לך היום?'
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
            {"role": "user", "parts": [f"המשתמש (user_id: {user_id}, name: {first_name}, age: {user_data[0]['age']}) התחבר לצ'אט. הנתונים שלו: {user_data}. אל תחזור על השם שלו בתשובות הבאות."]},
            {"role": "model", "parts": [greeting]}
        ]
        session['user_name'] = first_name  # Store name separately
        return jsonify({'response': greeting})

    # מצב שיחה פעילה
    if "next appointment" in user_message.lower() or "תור קרוב" in user_message or "תור הבא" in user_message:
        user_data = get_user_data(session['user_id'])
        next_appointment = find_next_appointment(user_data)
        if next_appointment:
            response_text = f"התור הבא שלך הוא ב־{next_appointment['appointment_date_Time__c']} מסוג {next_appointment['appointment_type']}."
        else:
            response_text = "לא מצאתי תורים עתידיים."
    else:
        # Debug: Print session state
        print(f"Debug - Session state: {session.get('state')}")
        print(f"Debug - User message: {user_message}")
        print(f"Debug - History length: {len(session.get('history', []))}")
        
        chat = session["model"].start_chat(history=session["history"])
        response = chat.send_message(user_message)
        session["history"] = chat.history
        response_text = response.text.strip()
        
        # Debug: Print response
        print(f"Debug - Response: {response_text}")
        
        # Post-process to remove unwanted repeated greetings and follow-up questions
        if session.get('user_name'):
            user_name = session['user_name']
            greeting_patterns = [f"שלום {user_name}", f"שלום {user_name}!", f"{user_name} שלום"]
            for pattern in greeting_patterns:
                if response_text.startswith(pattern):
                    # Remove the greeting part and continue with the rest
                    response_text = response_text.replace(pattern, "", 1).strip()
                    if response_text.startswith("!") or response_text.startswith(","):
                        response_text = response_text[1:].strip()
                    print(f"Debug - Removed greeting, new response: {response_text}")
                    break
        
        # Remove follow-up questions from the main response since we'll add them separately
        followup_patterns = [
            "האם תרצה פרטים נוספים על אחד מהתורים?",
            "יש לך שאלות על ההכנות לבדיקה או הנחיות הגעה?",
            "האם תרצה לדעת מה להביא לבדיקה או איך להגיע?",
            "האם תרצה הנחיות הגעה למתקן?",
            "האם תרצה לקבוע תור חדש או לבדוק תורים בתאריך אחר?",
            "יש לך שאלות על ההכנות לבדיקה?",
            "האם תרצה פרטים נוספים על",
            "יש לך עוד שאלות?",
            "מה עוד אוכל לעזור לך?"
        ]
        
        original_response = response_text
        for pattern in followup_patterns:
            if pattern in response_text:
                # Remove the follow-up question and any preceding punctuation/line breaks
                response_text = response_text.replace(pattern, "").strip()
                response_text = response_text.rstrip("?📝🗺️📋📅").strip()
                # Clean up multiple line breaks or trailing punctuation
                response_text = response_text.rstrip("<br>").rstrip("\n").strip()
                if response_text != original_response:
                    print(f"Debug - Removed follow-up question from main response")
                    break

    # בדיקה אם התשובה מכילה מידע על תורים ודורשת שאלת המשך
    responses = []
    formatted_response = format_bot_text(response_text)
    responses.append(formatted_response)
    
    # הוספת שאלת המשך אוטומטית לתשובות על תורים
    if should_add_followup_question(user_message, response_text):
        followup_question = generate_followup_question(user_message, response_text)
        if followup_question:
            responses.append(followup_question)
    
    if len(responses) == 1:
        return jsonify({'response': responses[0]})
    else:
        return jsonify({'responses': responses})

if __name__ == '__main__':
    app.run(debug=True)