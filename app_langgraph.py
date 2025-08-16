"""
Enhanced Flask application with LangGraph integration
This version integrates the original Flask app with LangGraph agents
"""

from flask import Flask, render_template, request, jsonify
import sqlite3
import google.generativeai as genai
import os
import re
from datetime import datetime
from dotenv import load_dotenv
from langgraph_config import create_agent
from clickhouse_mcp_agent import create_clickhouse_react_agent

load_dotenv()

app = Flask(__name__)

# Configure Gemini API
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# Initialize LangGraph agents
langgraph_agent = create_agent()
clickhouse_agent = create_clickhouse_react_agent()

# Chat sessions memory
chat_sessions = {}


def get_user_data(user_id):
    """Fetch user data from the database"""
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
    """Find the next upcoming appointment"""
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
    """Convert text with numbering/bullets to HTML lists and clean asterisks"""
    if not text:
        return ""
    if any(tag in text for tag in ("<ol", "<ul", "<li")):
        return text

    # Remove unnecessary asterisks
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


def should_use_analytics_agent(message: str) -> bool:
    """Determine if the message requires analytics/Clickhouse queries"""
    analytics_keywords = [
        "statistics", "analytics", "trends", "compare", "analysis",
        "report", "dashboard", "metrics", "insights", "data",
        "סטטיסטיקות", "ניתוח", "מגמות", "השוואה", "נתונים", "דוח"
    ]
    
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in analytics_keywords)


@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')


@app.route('/start', methods=['POST'])
def start_chat():
    """Start chat - request ID"""
    session_id = os.urandom(16).hex()
    chat_sessions[session_id] = {
        'state': 'waiting_for_id', 
        'history': [],
        'agent_type': 'gemini'  # Default to original Gemini agent
    }
    
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
    """Chat management with LangGraph integration"""
    session_id = request.json.get('session_id')
    user_message = request.json.get('message')
    use_analytics = request.json.get('use_analytics', False)  # Optional parameter

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
            greeting = f'שלום {first_name}! איך אוכל לעזור לך היום?'
        else:
            greeting = 'תודה! איך אני יכול לעזור לך היום?'

        # Initialize the original Gemini model for backward compatibility
        model = genai.GenerativeModel(
            'gemini-1.5-flash',
            system_instruction=system_prompt
        )
        
        session['user_id'] = user_id
        session['user_data'] = user_data
        session['state'] = 'chatting'
        session['model'] = model
        session['history'] = [
            {"role": "user", "parts": [f"המשתמש (user_id: {user_id}, age: {user_data[0]['age']}) התחבר. הנה הנתונים שלו: {user_data}"]},
            {"role": "model", "parts": ["שלום! אני הבוט של אסותא. איך אני יכול לעזור?"]}
        ]
        return jsonify({'response': greeting})

    # Active chat mode
    user_data = session.get('user_data', [])
    
    # Determine which agent to use
    if use_analytics or should_use_analytics_agent(user_message):
        # Use Clickhouse React agent for analytics queries
        try:
            thread_id = f"clickhouse_{session_id}"
            response_text = clickhouse_agent.run(
                user_input=user_message,
                user_data=user_data,
                thread_id=thread_id
            )
            session['agent_type'] = 'clickhouse_react'
        except Exception as e:
            print(f"Clickhouse agent error: {e}")
            response_text = "אני נתקלתי בשגיאה בעת ניתוח הנתונים. בינתיים, אענה לך באמצעות המערכת הרגילה."
            # Fallback to regular Gemini
            session['agent_type'] = 'gemini'
            
    elif "next appointment" in user_message.lower() or "תור קרוב" in user_message:
        # Quick response for next appointment
        next_appointment = find_next_appointment(user_data)
        if next_appointment:
            response_text = f"התור הבא שלך הוא ב־{next_appointment['appointment_date_Time__c']} מסוג {next_appointment['appointment_type']}."
        else:
            response_text = "לא מצאתי תורים עתידיים."
        session['agent_type'] = 'quick_response'
            
    else:
        # Use LangGraph agent for complex conversations
        try:
            thread_id = f"langgraph_{session_id}"
            response_text = langgraph_agent.run(
                user_input=user_message,
                user_id=session['user_id'],
                thread_id=thread_id
            )
            session['agent_type'] = 'langgraph'
        except Exception as e:
            print(f"LangGraph agent error: {e}")
            # Fallback to original Gemini chat
            chat = session["model"].start_chat(history=session["history"])
            response = chat.send_message(user_message)
            session["history"] = chat.history
            response_text = response.text.strip()
            session['agent_type'] = 'gemini_fallback'

    # Format response for display
    formatted_response = format_bot_text(response_text)
    
    return jsonify({
        'response': formatted_response,
        'agent_type': session.get('agent_type', 'unknown'),
        'debug_info': {
            'message_length': len(user_message),
            'uses_analytics': should_use_analytics_agent(user_message),
            'user_data_count': len(user_data)
        }
    })


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for LangGraph deployment"""
    return jsonify({
        'status': 'healthy',
        'agents': {
            'langgraph_agent': 'initialized',
            'clickhouse_agent': 'initialized'
        },
        'environment': {
            'has_gemini_key': bool(os.environ.get("GEMINI_API_KEY")),
            'has_openai_key': bool(os.environ.get("OPENAI_API_KEY")),
            'has_clickhouse_config': bool(os.environ.get("CLICKHOUSE_HOST"))
        }
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)