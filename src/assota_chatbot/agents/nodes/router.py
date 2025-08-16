"""Router node for determining query type and routing logic"""

import logging
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from ...config.settings import settings
from ...models.state_models import ReactAgentState

logger = logging.getLogger(__name__)


class QueryRouter:
    """Router for determining query intent and routing strategy"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openai.model,
            temperature=settings.openai.temperature,
            api_key=settings.openai.api_key
        )
    
    def route_query(self, state: ReactAgentState) -> ReactAgentState:
        """Determine if query requires database lookup or conversation"""
        user_input = state.get("user_input", "")
        user_id = state.get("user_id", "")
        iteration = state.get("iteration", 0)
        
        if iteration >= settings.agent.max_iterations:
            state["action"] = "Final Answer"
            state["action_input"] = "הגעתי למספר המקסימלי של ניסיונות."
            return state
        
        # Create routing prompt
        routing_prompt = self._create_routing_prompt(user_input, user_id)
        
        try:
            response = self.llm.invoke([HumanMessage(content=routing_prompt)])
            response_text = response.content
            
            # Parse response
            thought, action, action_input = self._parse_response(response_text)
            
            state["thought"] = thought
            state["action"] = action
            state["action_input"] = action_input
            state["iteration"] = iteration + 1
            state["current_step"] = "routing"
            
            logger.info(f"Routed query - Action: {action}, Type: {'medical' if action == 'clickhouse_query' else 'conversation'}")
            
        except Exception as e:
            logger.error(f"Router error: {str(e)}")
            state["thought"] = f"שגיאה בניתוב השאלה: {str(e)}"
            state["action"] = "Final Answer"
            state["action_input"] = "אני מתנצל, נתקלתי בשגיאה. איך אני יכול לעזור לך?"
        
        return state
    
    def _create_routing_prompt(self, user_input: str, user_id: str) -> str:
        """Create the routing prompt for query classification"""
        return f"""
You are a medical assistant router for Assota hospital. Analyze the user's query and decide how to handle it.

User query: {user_input}
User ID: {user_id}

ROUTING DECISION - Choose the appropriate action:

1. **General Conversation** - Use 'Final Answer' for:
   - Greetings (שלום, היי, איך שלומך)
   - General questions about the hospital
   - Small talk or non-medical queries
   - Questions that don't require database lookup

2. **Medical Data Query** - Use 'clickhouse_query' for:
   - Questions about appointments (תורים, פגישות)
   - Medical history or records
   - Test results or lab data
   - Any request for specific medical information
   - Requests for appointment details
   - Questions about getting to Assota facilities

DATABASE INFO (only use if SQL needed):
- Table: appointments_cleaned_for_bigquery
- MANDATORY: Every SQL query MUST include "WHERE user_id = '{user_id}'"
- Available columns:
  * user_id (String)
  * appointment_date_time_c (DateTime64) 
  * appoitment_type (String) - NOTE: missing 'n' in DB
  * appointment_status (String)
  * site_name, site_address, record_type

RESPONSE FORMAT:
Thought: [Determine if this needs database lookup or direct response]
Action: [clickhouse_query for data requests, Final Answer for conversation]
Action Input: [SQL query with user_id filter OR Hebrew conversational response]
"""
    
    def _parse_response(self, response_text: str) -> tuple[str, str, str]:
        """Parse the LLM response into thought, action, and action_input"""
        lines = response_text.strip().split('\n')
        thought = ""
        action = "Final Answer"
        action_input = "אני כאן לעזור לך!"
        
        for line in lines:
            line = line.strip()
            if line.startswith("Thought:"):
                thought = line[8:].strip()
            elif line.startswith("Action:"):
                action = line[7:].strip()
            elif line.startswith("Action Input:"):
                action_input = line[13:].strip()
        
        return thought, action, action_input


def create_router_node() -> callable:
    """Factory function to create router node"""
    router = QueryRouter()
    return router.route_query