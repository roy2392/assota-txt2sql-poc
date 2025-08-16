"""
React Agent with Clickhouse MCP integration for Assota Text2SQL POC
This agent uses the Model Context Protocol to interact with Clickhouse database
"""

import os
import json
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from typing_extensions import TypedDict
import subprocess


class ClickhouseMCPTool:
    """
    Tool to execute Clickhouse queries via MCP
    """
    
    def __init__(self):
        self.name = "clickhouse_query"
        self.description = "Execute SQL queries against Clickhouse database for analytics and data retrieval"
        self.mcp_config = {
            "command": "uv",
            "args": [
                "run",
                "--with",
                "mcp-clickhouse",
                "--python",
                "3.11",
                "mcp-clickhouse"
            ],
            "env": {
                "CLICKHOUSE_HOST": os.environ.get("CLICKHOUSE_HOST", "ra8f4bs5ok.eu-central-1.aws.clickhouse.cloud"),
                "CLICKHOUSE_PORT": os.environ.get("CLICKHOUSE_PORT", "8443"),
                "CLICKHOUSE_USER": os.environ.get("CLICKHOUSE_USER", "default"),
                "CLICKHOUSE_PASSWORD": os.environ.get("CLICKHOUSE_PASSWORD", "89Y9.vJt~7wcg"),
                "CLICKHOUSE_SECURE": os.environ.get("CLICKHOUSE_SECURE", "true"),
                "CLICKHOUSE_VERIFY": os.environ.get("CLICKHOUSE_VERIFY", "true"),
                "CLICKHOUSE_CONNECT_TIMEOUT": os.environ.get("CLICKHOUSE_CONNECT_TIMEOUT", "30"),
                "CLICKHOUSE_SEND_RECEIVE_TIMEOUT": os.environ.get("CLICKHOUSE_SEND_RECEIVE_TIMEOUT", "30")
            }
        }
    
    def _run(self, query: str) -> str:
        """
        Execute a Clickhouse query using MCP
        """
        print(f"🔍 Executing Clickhouse query: {query[:100]}...")
        
        try:
            # Validate query to prevent injection attacks
            if not query.strip():
                return "Error: Empty query provided"
            
            # Basic SQL injection prevention (basic check)
            dangerous_keywords = ['drop', 'delete', 'truncate', 'alter', 'create', 'insert', 'update']
            query_lower = query.lower()
            for keyword in dangerous_keywords:
                if keyword in query_lower:
                    return f"Error: Potentially dangerous SQL keyword '{keyword}' detected. Only SELECT queries are allowed."
            
            # Prepare the environment
            env = os.environ.copy()
            env.update(self.mcp_config["env"])
            
            # Create the MCP request
            mcp_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "execute_query",
                    "arguments": {
                        "query": query
                    }
                }
            }
            
            print("📡 Sending MCP request to Clickhouse...")
            
            # Execute the MCP command
            cmd = self.mcp_config["command"]
            args = self.mcp_config["args"]
            
            process = subprocess.run(
                [cmd] + args,
                input=json.dumps(mcp_request),
                capture_output=True,
                text=True,
                env=env,
                timeout=60
            )
            
            if process.returncode == 0:
                try:
                    response = json.loads(process.stdout)
                    if "result" in response:
                        result_data = response["result"]
                        print(f"✅ Query executed successfully, got {len(str(result_data))} characters of data")
                        return json.dumps(result_data, indent=2, ensure_ascii=False)
                    elif "error" in response:
                        error_msg = response["error"]
                        print(f"❌ MCP returned error: {error_msg}")
                        return f"Database error: {error_msg}"
                    else:
                        print(f"⚠️  Unexpected response format: {response}")
                        return f"Query executed but unexpected response format: {response}"
                except json.JSONDecodeError as e:
                    print(f"⚠️  Failed to parse JSON response: {e}")
                    return f"Raw output: {process.stdout}"
            else:
                error_output = process.stderr or process.stdout
                print(f"❌ Process failed with return code {process.returncode}: {error_output}")
                return f"Error executing query (code {process.returncode}): {error_output}"
        
        except subprocess.TimeoutExpired:
            print("⏰ Query timed out")
            return "Query timed out after 60 seconds"
        except Exception as e:
            print(f"💥 Unexpected error: {e}")
            return f"Error executing Clickhouse query: {str(e)}"
    
    def run(self, query: str) -> str:
        """Public interface to run queries"""
        return self._run(query)


class ReactAgentState(TypedDict):
    """
    State for the React agent
    """
    messages: List[BaseMessage]
    user_id: str
    user_data: List[Dict[str, Any]]
    current_step: str
    thought: str
    action: str
    action_input: str
    observation: str
    final_answer: str
    iteration_count: int
    max_iterations: int


class ClickhouseReactAgent:
    """
    React (Reasoning and Acting) Agent with Clickhouse MCP integration
    """
    
    def __init__(self, max_iterations: int = 5):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1,
            api_key=os.environ.get("OPENAI_API_KEY")
        )
        
        self.clickhouse_tool = ClickhouseMCPTool()
        self.max_iterations = max_iterations
        
        # React prompt template
        self.react_prompt = ChatPromptTemplate.from_template("""
You are a medical assistant for Assota hospital with access to a Clickhouse database for analytics.
You use a React (Reasoning and Acting) approach to solve problems step by step.
You MUST respond in Hebrew for all final answers.

Available tools:
- clickhouse_query: Execute SQL queries against Clickhouse database for analytics, trends, and statistical data

Guidelines for SQL generation:
- Use proper Clickhouse SQL syntax
- For appointment data, common tables include: appointments, accounts, lab_results, medical_records
- Common columns: user_id, appointment_date_Time__c, appointment_type, status, user_name, age
- Use aggregations like COUNT(), AVG(), SUM(), MAX(), MIN() for statistics
- Use GROUP BY for categorical analysis
- Use DATE functions for time-based analysis
- Always include WHERE conditions to filter relevant data

User Information: {user_data}
Current Question: {question}

You should follow this format:
Thought: [your reasoning about what to do next - think about what SQL query would answer the user's question]
Action: [the action to take, either 'clickhouse_query' or 'Final Answer']
Action Input: [if clickhouse_query: provide a well-formed SQL query; if Final Answer: provide your response]
Observation: [the result of the action will be shown here]

Continue this Thought/Action/Action Input/Observation cycle until you have enough information to provide a Final Answer in Hebrew.

Previous steps:
{previous_steps}

Now continue with your next step:
Thought:""")
        
        # Initialize the graph
        self.graph = self._create_graph()
    
    def _create_graph(self) -> StateGraph:
        """Create the React agent workflow"""
        
        workflow = StateGraph(ReactAgentState)
        
        # Define nodes
        workflow.add_node("think", self.think)
        workflow.add_node("act", self.act)
        workflow.add_node("observe", self.observe)
        workflow.add_node("finalize", self.finalize)
        
        # Define the flow
        workflow.set_entry_point("think")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "think",
            self._should_continue,
            {
                "continue": "act",
                "finish": "finalize"
            }
        )
        workflow.add_edge("act", "observe")
        workflow.add_edge("observe", "think")
        workflow.add_edge("finalize", END)
        
        return workflow.compile()
    
    def _should_continue(self, state: ReactAgentState) -> str:
        """Decide whether to continue thinking or finish"""
        if state.get("iteration_count", 0) >= state.get("max_iterations", self.max_iterations):
            return "finish"
        
        if state.get("action", "").lower() == "final answer":
            return "finish"
        
        return "continue"
    
    def think(self, state: ReactAgentState) -> ReactAgentState:
        """Think step - generate reasoning and decide on action"""
        messages = state.get("messages", [])
        user_data = state.get("user_data", [])
        iteration_count = state.get("iteration_count", 0)
        
        if not messages:
            return state
        
        # Build previous steps context
        previous_steps = ""
        if iteration_count > 0:
            previous_steps = f"""
Previous Thought: {state.get('thought', '')}
Previous Action: {state.get('action', '')}
Previous Action Input: {state.get('action_input', '')}
Previous Observation: {state.get('observation', '')}
"""
        
        # Get the user's question
        question = ""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                question = msg.content
                break
        
        # Generate thought and action
        prompt = self.react_prompt.format(
            user_data=json.dumps(user_data, indent=2),
            question=question,
            previous_steps=previous_steps
        )
        
        response = self.llm.invoke([HumanMessage(content=prompt)])
        response_text = response.content
        
        # Parse the response
        thought, action, action_input = self._parse_react_response(response_text)
        
        state["thought"] = thought
        state["action"] = action
        state["action_input"] = action_input
        state["iteration_count"] = iteration_count + 1
        state["current_step"] = "thinking"
        
        return state
    
    def act(self, state: ReactAgentState) -> ReactAgentState:
        """Act step - execute the planned action"""
        action = state.get("action", "")
        action_input = state.get("action_input", "")
        
        state["current_step"] = "acting"
        
        if action.lower() == "clickhouse_query":
            # Execute Clickhouse query
            result = self.clickhouse_tool._run(action_input)
            state["observation"] = result
        else:
            state["observation"] = f"Unknown action: {action}"
        
        return state
    
    def observe(self, state: ReactAgentState) -> ReactAgentState:
        """Observe step - process the action result"""
        state["current_step"] = "observing"
        # The observation is already set in the act step
        return state
    
    def finalize(self, state: ReactAgentState) -> ReactAgentState:
        """Finalize step - generate final answer"""
        messages = state.get("messages", [])
        user_data = state.get("user_data", [])
        thought = state.get("thought", "")
        observation = state.get("observation", "")
        
        # Generate final response
        final_prompt = f"""
Based on your analysis and the data you've gathered, provide a helpful response to the user.

User Data: {json.dumps(user_data, indent=2)}
Your Last Thought: {thought}
Your Last Observation: {observation}

Provide a clear, helpful response in Hebrew (as this is for an Israeli hospital):
"""
        
        response = self.llm.invoke([HumanMessage(content=final_prompt)])
        final_answer = response.content
        
        state["final_answer"] = final_answer
        state["current_step"] = "completed"
        
        # Add the final answer to messages
        messages.append(AIMessage(content=final_answer))
        state["messages"] = messages
        
        return state
    
    def _parse_react_response(self, response: str) -> tuple[str, str, str]:
        """Parse the React format response"""
        thought = ""
        action = ""
        action_input = ""
        
        lines = response.strip().split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if line.startswith("Thought:"):
                current_section = "thought"
                thought = line[8:].strip()
            elif line.startswith("Action:"):
                current_section = "action"
                action = line[7:].strip()
            elif line.startswith("Action Input:"):
                current_section = "action_input"
                action_input = line[13:].strip()
            elif current_section and line:
                if current_section == "thought":
                    thought += " " + line
                elif current_section == "action":
                    action += " " + line
                elif current_section == "action_input":
                    action_input += " " + line
        
        return thought.strip(), action.strip(), action_input.strip()
    
    def run(self, user_input: str, user_data: List[Dict[str, Any]] = None, thread_id: str = "default") -> str:
        """Run the React agent"""
        if user_data is None:
            user_data = []
        
        print(f"🤖 Starting React agent for query: {user_input[:50]}...")
        print(f"📊 User data provided: {len(user_data)} records")
        
        initial_state: ReactAgentState = {
            "messages": [HumanMessage(content=user_input)],
            "user_id": "",
            "user_data": user_data,
            "current_step": "initializing",
            "thought": "",
            "action": "",
            "action_input": "",
            "observation": "",
            "final_answer": "",
            "iteration_count": 0,
            "max_iterations": self.max_iterations
        }
        
        try:
            config = {"configurable": {"thread_id": thread_id}}
            result = self.graph.invoke(initial_state, config=config)
            
            final_answer = result.get("final_answer", "לא הצלחתי לעבד את הבקשה שלך.")
            print(f"✅ React agent completed. Answer length: {len(final_answer)} characters")
            
            return final_answer
        
        except Exception as e:
            print(f"❌ React Agent error: {e}")
            import traceback
            traceback.print_exc()
            return "אני נתקלתי בשגיאה בעת עיבוד הבקשה. אנא נסה שוב."


def create_clickhouse_react_agent(max_iterations: int = 5) -> ClickhouseReactAgent:
    """
    Factory function to create and return a configured React agent with Clickhouse MCP
    """
    return ClickhouseReactAgent(max_iterations=max_iterations)