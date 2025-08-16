"""Main entry point for the Assota Medical Chatbot"""

import sys
from pathlib import Path

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from assota_chatbot.agents.workflows.react_agent import create_react_agent
from assota_chatbot.config.settings import settings
from assota_chatbot.utils.logging import setup_logging
from assota_chatbot.models.state_models import ReactAgentState


def test_agent_with_user_id():
    """Test function to verify the refactored agent works"""
    # Setup logging
    setup_logging(level="INFO")
    
    # Create agent
    agent = create_react_agent()
    
    # Test state with user_id from actual data
    test_state: ReactAgentState = {
        "messages": [],
        "user_input": "מה התורים שלי?",  # "What are my appointments?"
        "user_id": "0014J00000JAuIGQA1",  # Real user_id with 19 appointments
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
        result = agent.invoke(test_state)
        print(f"Final answer: {result.get('final_answer', 'No final answer')}")
        print(f"Thought: {result.get('thought', 'No thought')}")
        print(f"Action: {result.get('action', 'No action')}")
        print(f"Observation: {result.get('observation', 'No observation')}")
        print(f"Iteration: {result.get('iteration', 'No iteration')}")
        return result
    except Exception as e:
        print(f"Test error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    test_agent_with_user_id()