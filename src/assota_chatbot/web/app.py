"""Flask web application for the Assota Medical Chatbot"""

import sys
from pathlib import Path
from flask import Flask, render_template, request, jsonify
import logging

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from assota_chatbot.agents.workflows.react_agent import create_react_agent
from assota_chatbot.config.settings import settings
from assota_chatbot.utils.logging import setup_logging, get_logger
from assota_chatbot.models.state_models import ReactAgentState
from assota_chatbot.models.data_schemas import UserQuery, AgentResponse

# Setup logging
setup_logging(level="INFO")
logger = get_logger("web.app")

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Initialize agent
agent = create_react_agent()

# Store user sessions in memory (in production, use Redis or database)
user_sessions = {}

@app.route('/')
def index():
    """Serve the main chat interface"""
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start_session():
    """Start a new chat session with user ID"""
    import uuid
    
    data = request.get_json() or {}
    user_id = data.get('user_id')
    
    session_id = str(uuid.uuid4())
    
    # If no user_id provided, return basic greeting (for legacy support)
    if not user_id:
        return jsonify({
            "session_id": session_id,
            "response": "שלום! אני אסי, עוזר ה-AI של אסותא. איך אני יכול לעזור לך היום?"
        })
    
    # Create initial agent state to get personalized greeting
    agent_state: ReactAgentState = {
        "messages": [],
        "user_input": "שלום",  # Initial greeting request
        "user_id": user_id,
        "thought": "",
        "action": "",
        "action_input": "",
        "observation": "",
        "final_answer": "",
        "iteration": 0,
        "current_step": "initializing",
        "max_iterations": settings.agent.max_iterations,
        "user_data": None,
        "context": None
    }
    
    try:
        # Store user_id in session
        user_sessions[session_id] = user_id
        
        # Get personalized greeting from agent
        result = agent.invoke(agent_state)
        response_text = result.get("final_answer", "שלום! איך אני יכול לעזור לך היום?")
        
        logger.info(f"Started session for user {user_id}")
        return jsonify({
            "session_id": session_id,
            "response": response_text,
            "user_id": user_id
        })
        
    except Exception as e:
        logger.error(f"Error starting session for user {user_id}: {str(e)}")
        # Still store user_id even if agent fails
        user_sessions[session_id] = user_id
        return jsonify({
            "session_id": session_id,
            "response": "שלום! איך אני יכול לעזור לך היום?",
            "user_id": user_id
        })

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat requests from the UI"""
    try:
        data = request.get_json()
        
        # Extract session_id and message from frontend request
        session_id = data.get('session_id')
        message = data.get('message')
        
        if not session_id or not message:
            return jsonify({
                "error": "Missing session_id or message"
            }), 400
        
        # Get user_id from session (fallback to session_id for legacy)
        user_id = user_sessions.get(session_id, session_id)
        
        # Create agent state
        agent_state: ReactAgentState = {
            "messages": [],
            "user_input": message,
            "user_id": user_id,
            "thought": "",
            "action": "",
            "action_input": "",
            "observation": "",
            "final_answer": "",
            "iteration": 0,
            "current_step": "initializing",
            "max_iterations": settings.agent.max_iterations,
            "user_data": None,
            "context": None
        }
        
        # Run agent
        result = agent.invoke(agent_state)
        
        # Return response in format expected by frontend
        response_text = result.get("final_answer", "אני מתנצל, נתקלתי בשגיאה.")
        
        logger.info(f"Chat request processed for session {session_id}")
        return jsonify({
            "response": response_text
        })
        
    except Exception as e:
        logger.error(f"Chat request failed: {str(e)}")
        return jsonify({
            "response": "אני מתנצל, נתקלתי בשגיאה בעת עיבוד הבקשה."
        }), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "version": "1.0.0"})

@app.route('/test')
def test():
    """Test endpoint for development"""
    try:
        # Test with sample data
        test_state: ReactAgentState = {
            "messages": [],
            "user_input": "שלום",
            "user_id": "test_user",
            "thought": "",
            "action": "",
            "action_input": "",
            "observation": "",
            "final_answer": "",
            "iteration": 0,
            "current_step": "initializing",
            "max_iterations": settings.agent.max_iterations,
            "user_data": None,
            "context": None
        }
        
        result = agent.invoke(test_state)
        return jsonify({
            "status": "success",
            "final_answer": result.get("final_answer", "No response"),
            "action": result.get("action", "No action"),
            "iteration": result.get("iteration", 0)
        })
        
    except Exception as e:
        logger.error(f"Test endpoint failed: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

def create_app():
    """Application factory"""
    return app

if __name__ == '__main__':
    app.run(
        host=settings.host,
        port=3001,  # Use port 3001
        debug=settings.debug
    )