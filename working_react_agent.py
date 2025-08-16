"""
Working React Agent with ClickHouse MCP integration for LangGraph Studio
"""

import os
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from typing_extensions import TypedDict
from dotenv import load_dotenv

# Load environment variables at module level
load_dotenv()


class ReactAgentState(TypedDict):
    """State for React agent"""
    messages: List[BaseMessage]
    user_input: str
    user_id: str
    thought: str
    action: str
    action_input: str
    observation: str
    final_answer: str
    iteration: int


def create_react_agent():
    """Create a working React agent for LangGraph Studio"""
    
    # Initialize LLM
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.1,
        api_key=os.environ.get("OPENAI_API_KEY")
    )
    
    def think_step(state: ReactAgentState) -> ReactAgentState:
        """Think step - generate reasoning and action"""
        user_input = state.get("user_input", "")
        iteration = state.get("iteration", 0)
        
        if iteration >= 3:  # Max iterations
            state["action"] = "Final Answer"
            state["action_input"] = "I've reached the maximum number of iterations."
            return state
        
        # Get user_id from state
        user_id = state.get("user_id", "")
        
        # Create thinking prompt with routing logic
        prompt = f"""
You are a medical assistant for Assota hospital that can help with both general conversation and medical data queries.

User query: {user_input}
User ID: {user_id}

ROUTING DECISION - Analyze the user's query and decide:

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
   - any request for a specific appointment 
   - any request regarding how to get to specific Assuta facility (use the site_instructions column)

DATABASE INFO (only use if SQL needed):
- Table: appointments_cleaned_for_bigquery
- MANDATORY: Every SQL query MUST include "WHERE user_id = '{user_id}'"
- Available data: appointments, dates, types, status for this user
- CORRECT COLUMN NAMES (use exactly these):
  * user_id (String)
  * appointment_date_time_c (DateTime64) 
  * appoitment_type (String) - NOTE: missing 'n' in DB
  * appointment_status (String)
  * site_name, site_address, record_type

SQL EXAMPLES (only if data query needed - USE CORRECT COLUMN NAMES):
- Appointments: SELECT * FROM appointments_cleaned_for_bigquery WHERE user_id = '{user_id}' ORDER BY appointment_date_time_c DESC LIMIT 10
- Counts: SELECT COUNT(*) as total FROM appointments_cleaned_for_bigquery WHERE user_id = '{user_id}'
- Types: SELECT appoitment_type, COUNT(*) FROM appointments_cleaned_for_bigquery WHERE user_id = '{user_id}' GROUP BY appoitment_type

RESPONSE FORMAT:
Thought: [Determine if this needs database lookup or can be answered directly]
Action: [clickhouse_query for data requests, Final Answer for general conversation]
Action Input: [SQL query with WHERE user_id = '{user_id}' OR Hebrew conversational response]
"""
        
        try:
            response = llm.invoke([HumanMessage(content=prompt)])
            response_text = response.content
            
            # Parse response
            lines = response_text.strip().split('\n')
            thought = ""
            action = "Final Answer"
            action_input = "I'm ready to help you!"
            
            for line in lines:
                if line.startswith("Thought:"):
                    thought = line[8:].strip()
                elif line.startswith("Action:"):
                    action = line[7:].strip()
                elif line.startswith("Action Input:"):
                    action_input = line[13:].strip()
            
            state["thought"] = thought
            state["action"] = action
            state["action_input"] = action_input
            state["iteration"] = iteration + 1
            
        except Exception as e:
            state["thought"] = f"Error in thinking: {str(e)}"
            state["action"] = "Final Answer"
            state["action_input"] = "אני מתנצל, נתקלתי בשגיאה. איך אני יכול לעזור לך?"
        
        return state
    
    def act_step(state: ReactAgentState) -> ReactAgentState:
        """Act step - execute the action"""
        action = state.get("action", "")
        action_input = state.get("action_input", "")
        user_id = state.get("user_id", "")
        
        if action == "clickhouse_query":
            # Execute real ClickHouse query using proper MCP session management
            try:
                import asyncio
                from mcp import ClientSession, StdioServerParameters
                from mcp.client.stdio import stdio_client
                
                # Fix the query to use the correct table name (only if not already correct)
                if "FROM appointments " in action_input and "appointments_cleaned_for_bigquery" not in action_input:
                    action_input = action_input.replace("appointments", "appointments_cleaned_for_bigquery")
                
                # Validate that user_id is included in the query for security
                if user_id and f"user_id = '{user_id}'" not in action_input:
                    state["observation"] = f"Error: Query must include user_id filter for data privacy. User ID: {user_id}"
                    return state
                
                # Execute the query with proper session management
                async def run_query():
                    # Environment configuration for ClickHouse
                    env = {
                        "CLICKHOUSE_HOST": os.environ.get("CLICKHOUSE_HOST", "ra8f4bs5ok.eu-central-1.aws.clickhouse.cloud"),
                        "CLICKHOUSE_PORT": os.environ.get("CLICKHOUSE_PORT", "8443"),
                        "CLICKHOUSE_USER": os.environ.get("CLICKHOUSE_USER", "default"),
                        "CLICKHOUSE_PASSWORD": os.environ.get("CLICKHOUSE_PASSWORD", "89Y9.vJt~7wcg"),
                        "CLICKHOUSE_SECURE": os.environ.get("CLICKHOUSE_SECURE", "true"),
                        "CLICKHOUSE_VERIFY": os.environ.get("CLICKHOUSE_VERIFY", "true"),
                        "CLICKHOUSE_CONNECT_TIMEOUT": os.environ.get("CLICKHOUSE_CONNECT_TIMEOUT", "30"),
                        "CLICKHOUSE_SEND_RECEIVE_TIMEOUT": os.environ.get("CLICKHOUSE_SEND_RECEIVE_TIMEOUT", "30")
                    }
                    
                    # Server parameters for MCP
                    server_params = StdioServerParameters(
                        command="uv",
                        args=["run", "--with", "mcp-clickhouse", "--python", "3.11", "mcp-clickhouse"],
                        env=env
                    )
                    
                    try:
                        async with stdio_client(server_params) as (read, write):
                            async with ClientSession(read, write) as session:
                                await session.initialize()
                                
                                print(f"📊 Executing query: {action_input}")
                                result = await session.call_tool("run_select_query", {"query": action_input})
                                print(f"📄 Raw result: {result}")
                                
                                if result.content and len(result.content) > 0:
                                    content = result.content[0]
                                    if hasattr(content, 'text'):
                                        return content.text
                                    else:
                                        return str(content)
                                else:
                                    return "No results returned"
                    except Exception as e:
                        print(f"❌ MCP Error: {type(e).__name__}: {str(e)}")
                        return f"Error executing query: {str(e)}"
                
                # Run the async function
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(run_query())
                    state["observation"] = f"Query executed successfully for user {user_id}. Results: {result}"
                finally:
                    loop.close()
                
            except Exception as e:
                print(f"ClickHouse query error: {e}")
                state["observation"] = f"Error executing ClickHouse query: {str(e)}"
        
        elif action == "Final Answer":
            # Generate final Hebrew response
            user_input = state.get('user_input', '')
            observation = state.get('observation', '')
            user_id = state.get('user_id', '')
            
            final_prompt = f"""
You are a helpful medical assistant for Assota hospital. Based on the database query results, provide a helpful response in Hebrew.

User question: {user_input}
User ID: {user_id}
Database query results: {observation}

Instructions:
- Respond in Hebrew
- If the query was successful and returned data, summarize the appointment information
- If there was an error or no data, explain that no appointments were found and offer to help
- Be friendly and professional

Provide your response in Hebrew:
"""
            try:
                response = llm.invoke([HumanMessage(content=final_prompt)])
                state["final_answer"] = response.content
            except Exception as e:
                state["final_answer"] = "שלום! איך אני יכול לעזור לך היום?"
        
        return state
    
    def should_continue(state: ReactAgentState) -> str:
        """Decide whether to continue or finish"""
        action = state.get("action", "")
        iteration = state.get("iteration", 0)
        observation = state.get("observation", "")
        
        # If we have an observation from a SQL query, generate final answer based on data
        if action == "clickhouse_query" and observation:
            return "generate_final"
        
        # If we chose Final Answer for conversation, go directly to finish
        if action == "Final Answer":
            return "finish"
            
        # If we hit max iterations, finish
        if iteration >= 3:
            return "finish"
            
        return "continue"
    
    def generate_final_answer(state: ReactAgentState) -> ReactAgentState:
        """Generate final Hebrew response based on query results"""
        user_input = state.get('user_input', '')
        observation = state.get('observation', '')
        user_id = state.get('user_id', '')
        
        final_prompt = f"""
You are a helpful medical assistant for Assota hospital. Based on the database query results, provide a helpful response in Hebrew.

User question: {user_input}
User ID: {user_id}
Database query results: {observation}

Instructions:
- Respond in Hebrew in a friendly, professional manner
- Analyze what type of medical information the user requested:
  * Appointments (תורים): Summarize dates, types, status
  * Medical history: Explain relevant findings
  * Statistics: Present counts or trends clearly
  * Test results: Explain what was found
- If the query was successful and returned data, provide a clear summary
- If there was an error or no data found, explain this politely and offer to help with other questions
- Always maintain patient privacy - only discuss this user's own data

Based on the user's question about: {user_input}
Provide your response in Hebrew:
"""
        try:
            llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.1,
                api_key=os.environ.get("OPENAI_API_KEY")
            )
            response = llm.invoke([HumanMessage(content=final_prompt)])
            state["final_answer"] = response.content
        except Exception as e:
            state["final_answer"] = "שלום! איך אני יכול לעזור לך היום?"
        
        return state
    
    # Create the graph
    workflow = StateGraph(ReactAgentState)
    
    # Add nodes
    workflow.add_node("think", think_step)
    workflow.add_node("act", act_step)
    workflow.add_node("generate_final", generate_final_answer)
    workflow.add_node("finish", lambda state: state)
    
    # Set entry point
    workflow.set_entry_point("think")
    
    # Add edges
    workflow.add_edge("think", "act")
    workflow.add_conditional_edges(
        "act",
        should_continue,
        {
            "continue": "think",
            "generate_final": "generate_final",
            "finish": "finish"
        }
    )
    workflow.add_edge("generate_final", "finish")
    workflow.add_edge("finish", END)
    
    return workflow.compile()


# This is the required export for LangGraph Studio
graph = create_react_agent()


def test_agent_with_user_id():
    """Test function to verify user_id filtering works"""
    agent = create_react_agent()
    
    # Test state with user_id from the actual data
    test_state = {
        "messages": [],
        "user_input": "מה התורים שלי?",  # "What are my appointments?"
        "user_id": "0014J00000JAuIGQA1",  # Real user_id with 19 appointments
        "thought": "",
        "action": "",
        "action_input": "",
        "observation": "",
        "final_answer": "",
        "iteration": 0
    }
    
    try:
        result = agent.invoke(test_state)
        print(f"Final answer: {result.get('final_answer', 'No final answer')}")
        print(f"Thought: {result.get('thought', 'No thought')}")
        print(f"Action: {result.get('action', 'No action')}")
        print(f"Action Input: {result.get('action_input', 'No action input')}")
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