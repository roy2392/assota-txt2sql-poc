"""Response generation node for creating Hebrew medical responses"""

import logging
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from ...config.settings import settings
from ...models.state_models import ReactAgentState

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """Generates final Hebrew responses based on query results"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openai.model,
            temperature=settings.openai.temperature,
            api_key=settings.openai.api_key
        )
    
    def generate_response(self, state: ReactAgentState) -> ReactAgentState:
        """Generate final Hebrew response based on observation data"""
        user_input = state.get('user_input', '')
        observation = state.get('observation', '')
        user_id = state.get('user_id', '')
        action = state.get('action', '')
        
        state["current_step"] = "responding"
        
        # If we already have a final answer (from direct conversation), use it
        if action == "Final Answer" and state.get("final_answer"):
            return state
        
        # Handle different types of queries based on action and content
        if user_input.strip() in ['שלום', 'היי', 'בוקר טוב', 'צהריים טובים', 'ערב טוב']:
            # Initial greeting
            final_answer = self._generate_greeting_response(user_id)
        elif observation and "Query executed successfully" in observation:
            # Database query with results
            final_answer = self._generate_medical_response(user_input, observation, user_id)
        elif action == "Final Answer":
            # Router determined this should be handled as conversation (not database query)
            final_answer = self._generate_conversation_response(user_input, user_id)
        else:
            # Error or fallback
            final_answer = self._generate_error_response(user_input, observation)
        
        state["final_answer"] = final_answer
        logger.info(f"Generated response for user {user_id} - Length: {len(final_answer)} chars")
        
        return state
    
    def _generate_medical_response(self, user_input: str, observation: str, user_id: str) -> str:
        """Generate Hebrew response for medical data queries"""
        # Load system prompt from file
        system_prompt_content = self._load_system_prompt()
        
        prompt = f"""
{system_prompt_content}

שאלת המשתמש: {user_input}
מזהה משתמש: {user_id}
תוצאות השאילתה: {observation}

עליך לפעול בהתאם להוראות המערכת הנ"ל ולהגיב בדיוק כפי שמצוין בדוגמאות השיחה.

**כלל עליון: לפני כל תשובה, בדוק אם קיימת דוגמה רלוונטית בסעיף "דוגמאות שיחה". אם כן, ענה באופן זהה לחלוטין לדוגמה.**

הגב בעברית עם אימוג'ים רלוונטיים וטון מקצועי תומך:
"""
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            return response.content
        except Exception as e:
            logger.error(f"Error generating medical response: {str(e)}")
            return "שלום! איך אני יכול לעזור לך היום?"
    
    def _generate_greeting_response(self, user_id: str) -> str:
        """Generate personalized greeting according to system_prompt.txt"""
        try:
            # For now, return the standard greeting format from system_prompt
            # TODO: Add personalized name once we know the correct table structure
            return "שלום! כיצד אוכל לעזור לך?"
        except Exception as e:
            logger.error(f"Error generating greeting: {str(e)}")
            return "שלום! כיצד אוכל לעזור לך?"
    
    def _generate_conversation_response(self, user_input: str, user_id: str) -> str:
        """Generate response for conversational queries using system prompt"""
        # Load system prompt from file
        system_prompt_content = self._load_system_prompt()
        
        prompt = f"""
{system_prompt_content}

שאלת המשתמש: {user_input}
מזהה משתמש: {user_id}

זהו שאלה כללית שלא דורשת שאילתת מסד נתונים. 
עליך לפעול בהתאם להוראות המערכת הנ"ל ולהגיב בדיוק כפי שמצוין בדוגמאות השיחה.

**כלל עליון: לפני כל תשובה, בדוק אם קיימת דוגמה רלוונטית בסעיף "דוגמאות שיחה". אם כן, ענה באופן זהה לחלוטין לדוגמה.**

הגב בעברית עם אימוג'ים רלוונטיים וטון מקצועי תומך:
"""
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            return response.content
        except Exception as e:
            logger.error(f"Error generating conversation response: {str(e)}")
            return "שלום! איך אני יכול לעזור לך היום?"
    
    def _get_user_data(self, user_id: str) -> dict:
        """Get user data from ClickHouse database"""
        try:
            import asyncio
            from ...tools.clickhouse.client import ClickHouseMCPClient
            
            clickhouse_client = ClickHouseMCPClient()
            query = f"SELECT firstname, lastname FROM accounts_cleaned_for_bigquery WHERE user_id = '{user_id}' LIMIT 1"
            
            # Create new event loop for async operations
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(clickhouse_client.execute_query(query))
                if result.record_count > 0 and result.rows:
                    return {
                        'firstname': result.rows[0][0] if len(result.rows[0]) > 0 else None,
                        'lastname': result.rows[0][1] if len(result.rows[0]) > 1 else None
                    }
                return {}
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"Error fetching user data: {str(e)}")
            return {}
    
    def _load_system_prompt(self) -> str:
        """Load system prompt from file"""
        try:
            from pathlib import Path
            system_prompt_path = Path(__file__).parent.parent.parent.parent / "system_prompt.txt"
            with open(system_prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error loading system prompt: {str(e)}")
            return ""
    
    def _generate_error_response(self, user_input: str, observation: str) -> str:
        """Generate Hebrew response for errors or failed queries"""
        if "Security error" in observation:
            return "אני מתנצל, נתקלתי בבעיית אבטחה בעת ניסיון לגשת לנתונים. אנא וודא שאתה מחובר כראוי למערכת."
        
        if "Error executing" in observation:
            return "שלום! איך אני יכול לעזור לך?"
        
        # General fallback
        return "שלום! איך אני יכול לעזור לך היום?"


def create_responder_node() -> callable:
    """Factory function to create responder node"""
    responder = ResponseGenerator()
    return responder.generate_response