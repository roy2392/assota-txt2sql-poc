"""Main React Agent workflow using LangGraph"""

import logging
from typing import Dict, Any
from langgraph.graph import StateGraph, END

from assota_chatbot.models.state_models import ReactAgentState
from assota_chatbot.agents.nodes.router import create_router_node
from assota_chatbot.agents.nodes.executor import create_executor_node
from assota_chatbot.agents.nodes.responder import create_responder_node

logger = logging.getLogger(__name__)


class ReactAgentWorkflow:
    """LangGraph workflow for the React agent"""
    
    def __init__(self):
        self.graph = self._create_graph()
    
    def _create_graph(self) -> StateGraph:
        """Create the LangGraph workflow"""
        workflow = StateGraph(ReactAgentState)
        
        # Create nodes
        router_node = create_router_node()
        executor_node = create_executor_node()
        responder_node = create_responder_node()
        
        # Add nodes to graph
        workflow.add_node("route", router_node)
        workflow.add_node("execute", executor_node)
        workflow.add_node("respond", responder_node)
        workflow.add_node("finish", lambda state: state)
        
        # Set entry point
        workflow.set_entry_point("route")
        
        # Add conditional routing logic
        workflow.add_conditional_edges(
            "route",
            self._should_execute_query,
            {
                "execute": "execute",
                "respond": "respond"
            }
        )
        
        # After execution, always generate response
        workflow.add_edge("execute", "respond")
        
        # After response, finish
        workflow.add_edge("respond", "finish")
        workflow.add_edge("finish", END)
        
        return workflow.compile()
    
    def _should_execute_query(self, state: ReactAgentState) -> str:
        """Decide whether to execute a query or generate direct response"""
        action = state.get("action", "")
        
        if action == "clickhouse_query":
            return "execute"
        else:
            # For "Final Answer" and other actions, go directly to response
            return "respond"
    
    def invoke(self, initial_state: Dict[str, Any]) -> ReactAgentState:
        """Run the workflow with initial state"""
        try:
            logger.info(f"Starting React agent workflow for user: {initial_state.get('user_id', 'unknown')}")
            result = self.graph.invoke(initial_state)
            logger.info("React agent workflow completed successfully")
            return result
        except Exception as e:
            logger.error(f"React agent workflow failed: {str(e)}")
            # Return error state
            return {
                **initial_state,
                "final_answer": "אני מתנצל, נתקלתי בשגיאה בעת עיבוד הבקשה. אנא נסה שוב.",
                "observation": f"Workflow error: {str(e)}",
                "current_step": "error"
            }


def create_react_agent() -> ReactAgentWorkflow:
    """Factory function to create React agent workflow"""
    return ReactAgentWorkflow()


# Export for LangGraph Studio
agent_workflow = create_react_agent()
graph = agent_workflow.graph