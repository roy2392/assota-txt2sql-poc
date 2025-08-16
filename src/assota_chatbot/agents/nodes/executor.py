"""Executor node for running actions (ClickHouse queries or direct responses)"""

import asyncio
import logging
from typing import Dict, Any

from ...models.state_models import ReactAgentState
from ...tools.clickhouse.client import clickhouse_client

logger = logging.getLogger(__name__)


class ActionExecutor:
    """Executes actions determined by the router"""
    
    def execute_action(self, state: ReactAgentState) -> ReactAgentState:
        """Execute the determined action"""
        action = state.get("action", "")
        action_input = state.get("action_input", "")
        user_id = state.get("user_id", "")
        
        state["current_step"] = "executing"
        
        if action == "clickhouse_query":
            # Execute ClickHouse query
            return self._execute_clickhouse_query(state, action_input, user_id)
        elif action == "Final Answer":
            # Direct response - no database query needed
            state["observation"] = "Direct response provided"
            state["final_answer"] = action_input
            return state
        else:
            # Unknown action
            logger.warning(f"Unknown action: {action}")
            state["observation"] = f"Unknown action: {action}"
            state["final_answer"] = "אני מתנצל, נתקלתי בשגיאה בעיבוד הבקשה."
            return state
    
    def _execute_clickhouse_query(
        self, 
        state: ReactAgentState, 
        query: str, 
        user_id: str
    ) -> ReactAgentState:
        """Execute ClickHouse query with proper error handling"""
        try:
            # Validate query contains user_id filter for security
            if user_id and f"user_id = '{user_id}'" not in query:
                state["observation"] = f"Security error: Query must include user_id filter. User ID: {user_id}"
                return state
            
            # Execute query asynchronously
            result = self._run_async_query(query)
            
            if result:
                state["observation"] = f"Query executed successfully for user {user_id}. Results: {result}"
                # Parse JSON to get record count for logging
                try:
                    import json
                    if result != "No records found":
                        result_data = json.loads(result)
                        record_count = result_data.get('record_count', 0)
                        logger.info(f"ClickHouse query successful - {record_count} records returned")
                    else:
                        logger.info("ClickHouse query successful - 0 records returned")
                except json.JSONDecodeError:
                    logger.info("ClickHouse query successful - result format unknown")
            else:
                state["observation"] = "Query executed but returned no results"
                logger.warning("ClickHouse query returned no results")
                
        except Exception as e:
            error_msg = f"Error executing ClickHouse query: {str(e)}"
            logger.error(error_msg)
            state["observation"] = error_msg
        
        return state
    
    def _run_async_query(self, query: str) -> str:
        """Run async ClickHouse query in new event loop"""
        try:
            # Create new event loop for async operations
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(clickhouse_client.execute_query(query))
                
                # Convert result to JSON string for observation
                if result.record_count > 0:
                    import json
                    return json.dumps({
                        "columns": result.columns,
                        "rows": result.rows,
                        "record_count": result.record_count
                    }, ensure_ascii=False, default=str)
                else:
                    return "No records found"
                    
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"Async query execution failed: {str(e)}")
            raise


def create_executor_node() -> callable:
    """Factory function to create executor node"""
    executor = ActionExecutor()
    return executor.execute_action