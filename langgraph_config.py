"""
LangGraph configuration for Assota Text2SQL POC
This file contains the configuration and setup for LangGraph deployment
"""

import os
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from typing_extensions import TypedDict
import sqlite3


class GraphState(TypedDict):
    """
    Represents the state of our conversation graph.
    
    Attributes:
        messages: List of messages in the conversation
        user_id: User identifier from the database
        user_data: User appointment and profile data
        clickhouse_query: SQL query to execute
        sql_results: Results from the SQL query
        next_appointment: Next upcoming appointment for the user
    """
    messages: list[BaseMessage]
    user_id: str
    user_data: list[Dict[str, Any]]
    clickhouse_query: str
    sql_results: list[Dict[str, Any]]
    next_appointment: Dict[str, Any]


class AssotaLangGraphAgent:
    """
    LangGraph agent for Assota medical chatbot with Clickhouse integration
    """
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1,
            api_key=os.environ.get("OPENAI_API_KEY")
        )
        
        # Use embedded system prompt to avoid blocking I/O
        self.system_prompt = """
        You are a helpful medical assistant for Assota hospital.
        You help patients with appointment information, medical queries, and general assistance.
        Always respond in Hebrew when appropriate for Israeli patients.
        Be empathetic, professional, and provide accurate information.
        """
        
        # Initialize the graph
        self.graph = self._create_graph()
    
    
    def _create_graph(self) -> StateGraph:
        """Create the LangGraph workflow"""
        
        workflow = StateGraph(GraphState)
        
        # Define nodes
        workflow.add_node("authenticate_user", self.authenticate_user)
        workflow.add_node("fetch_user_data", self.fetch_user_data)
        workflow.add_node("analyze_query", self.analyze_query)
        workflow.add_node("execute_clickhouse_query", self.execute_clickhouse_query)
        workflow.add_node("generate_response", self.generate_response)
        
        # Define the flow
        workflow.set_entry_point("authenticate_user")
        
        workflow.add_edge("authenticate_user", "fetch_user_data")
        workflow.add_edge("fetch_user_data", "analyze_query")
        workflow.add_edge("analyze_query", "execute_clickhouse_query")
        workflow.add_edge("execute_clickhouse_query", "generate_response")
        workflow.add_edge("generate_response", END)
        
        # Add checkpointer for memory
        memory = SqliteSaver.from_conn_string(":memory:")
        
        return workflow.compile(checkpointer=memory)
    
    def authenticate_user(self, state: GraphState) -> GraphState:
        """
        Authenticate user and extract user_id from messages
        """
        messages = state.get("messages", [])
        user_id = state.get("user_id", "")
        
        if not user_id and messages:
            # Try to extract user ID from the latest human message
            for message in reversed(messages):
                if isinstance(message, HumanMessage):
                    # Simple ID extraction - in production, this should be more robust
                    content = message.content.strip()
                    if content.isdigit() and len(content) >= 6:
                        user_id = content
                        break
        
        state["user_id"] = user_id
        return state
    
    def fetch_user_data(self, state: GraphState) -> GraphState:
        """
        Fetch user data from SQLite database
        """
        user_id = state.get("user_id", "")
        user_data = []
        
        if user_id:
            try:
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
            except Exception as e:
                print(f"Database error: {e}")
        
        state["user_data"] = user_data
        return state
    
    def analyze_query(self, state: GraphState) -> GraphState:
        """
        Analyze the user query to determine if Clickhouse query is needed
        """
        messages = state.get("messages", [])
        user_data = state.get("user_data", [])
        
        if not messages:
            return state
        
        latest_message = messages[-1]
        if isinstance(latest_message, HumanMessage):
            query_content = latest_message.content.lower()
            
            # Simple logic to determine if we need analytics
            needs_analytics = any(keyword in query_content for keyword in [
                "statistics", "analytics", "trends", "compare", "analysis",
                "report", "dashboard", "metrics", "insights"
            ])
            
            if needs_analytics and user_data:
                # Generate a Clickhouse query
                clickhouse_query = self._generate_clickhouse_query(query_content, user_data)
                state["clickhouse_query"] = clickhouse_query
        
        return state
    
    def _generate_clickhouse_query(self, query_content: str, user_data: list) -> str:
        """
        Generate a Clickhouse SQL query based on user intent and data
        """
        # This is a simple example - in production, use LLM to generate proper SQL
        base_query = """
        SELECT 
            appointment_type,
            COUNT(*) as total_appointments,
            AVG(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completion_rate
        FROM appointments 
        WHERE user_id = '{user_id}'
        GROUP BY appointment_type
        ORDER BY total_appointments DESC
        """
        
        if user_data:
            user_id = user_data[0].get('user_id', '')
            return base_query.format(user_id=user_id)
        
        return ""
    
    def execute_clickhouse_query(self, state: GraphState) -> GraphState:
        """
        Execute query against Clickhouse database using MCP
        """
        clickhouse_query = state.get("clickhouse_query", "")
        sql_results = []
        
        if clickhouse_query:
            # In a real implementation, this would use the Clickhouse MCP
            # For now, we'll simulate results
            sql_results = [
                {"appointment_type": "consultation", "total_appointments": 5, "completion_rate": 0.8},
                {"appointment_type": "lab_test", "total_appointments": 3, "completion_rate": 1.0}
            ]
        
        state["sql_results"] = sql_results
        return state
    
    def generate_response(self, state: GraphState) -> GraphState:
        """
        Generate final response using LLM
        """
        messages = state.get("messages", [])
        user_data = state.get("user_data", [])
        sql_results = state.get("sql_results", [])
        
        if not messages:
            return state
        
        # Create context for the LLM (context used in prompt below)
        
        # Generate response
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", "User data: {user_data}\nAnalytics results: {sql_results}\nUser query: {query}")
        ])
        
        latest_message = messages[-1]
        if isinstance(latest_message, HumanMessage):
            chain = prompt | self.llm
            response = chain.invoke({
                "user_data": str(user_data),
                "sql_results": str(sql_results),
                "query": latest_message.content
            })
            
            messages.append(AIMessage(content=response.content))
        
        state["messages"] = messages
        return state
    
    def run(self, user_input: str, user_id: str = "", thread_id: str = "default") -> str:
        """
        Run the agent with user input
        """
        config = {"configurable": {"thread_id": thread_id}}
        
        initial_state = {
            "messages": [HumanMessage(content=user_input)],
            "user_id": user_id,
            "user_data": [],
            "clickhouse_query": "",
            "sql_results": [],
            "next_appointment": {}
        }
        
        try:
            result = self.graph.invoke(initial_state, config=config)
            
            if result.get("messages"):
                last_message = result["messages"][-1]
                if isinstance(last_message, AIMessage):
                    return last_message.content
            
            return "I'm sorry, I couldn't process your request."
        
        except Exception as e:
            print(f"Agent error: {e}")
            return "I encountered an error processing your request. Please try again."


def create_agent() -> AssotaLangGraphAgent:
    """
    Factory function to create and return a configured LangGraph agent
    """
    return AssotaLangGraphAgent()