"""
Proper ClickHouse MCP integration using async MCP client (based on ClickHouse documentation)
"""
import os
import asyncio
from typing import Dict, Any, List
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage


async def load_mcp_tools(session):
    """Load MCP tools from session"""
    result = await session.call_tool("execute_query", {"query": "SHOW DATABASES"})
    return result


async def create_clickhouse_mcp_agent():
    """Create a React agent with ClickHouse MCP integration"""
    
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
        args=[
            "run",
            "--with", "mcp-clickhouse",
            "--python", "3.11",
            "mcp-clickhouse"
        ],
        env=env
    )
    
    # Initialize LLM
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.1,
        api_key=os.environ.get("OPENAI_API_KEY")
    )
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # List available tools
                tools_result = await session.list_tools()
                print(f"Available MCP tools: {tools_result}")
                
                # Create a simple tool wrapper
                async def execute_clickhouse_query(query: str) -> str:
                    """Execute a ClickHouse query via MCP"""
                    try:
                        print(f"📊 Executing query: {query}")
                        result = await session.call_tool("run_select_query", {"query": query})
                        print(f"📄 Raw result: {result}")
                        print(f"📋 Result content: {result.content}")
                        
                        if result.content and len(result.content) > 0:
                            content = result.content[0]
                            print(f"📑 Content type: {type(content)}")
                            print(f"📑 Content: {content}")
                            if hasattr(content, 'text'):
                                return str(content.text)
                            else:
                                return str(content)
                        else:
                            return "No results returned"
                    except Exception as e:
                        print(f"❌ Error details: {type(e).__name__}: {str(e)}")
                        import traceback
                        traceback.print_exc()
                        return f"Error executing query: {str(e)}"
                
                return execute_clickhouse_query
                
    except Exception as e:
        print(f"Error creating MCP agent: {e}")
        return None


async def test_user_query(user_id: str, query: str):
    """Test a user query with proper MCP integration"""
    print(f"Testing query: '{query}' for user_id: {user_id}")
    
    clickhouse_query_func = await create_clickhouse_mcp_agent()
    
    if not clickhouse_query_func:
        return "Failed to create ClickHouse MCP connection"
    
    # Create a SQL query with user_id filtering
    sql_query = f"""
    SELECT 
        appointment_date_Time__c,
        appointment_type,
        status,
        user_name
    FROM appointments_cleaned_for_bigquery 
    WHERE user_id = '{user_id}'
    ORDER BY appointment_date_Time__c DESC
    LIMIT 10
    """
    
    print(f"Executing SQL: {sql_query}")
    result = await clickhouse_query_func(sql_query)
    print(f"Result: {result}")
    
    return result


class AsyncClickHouseTool:
    """Async wrapper for ClickHouse MCP tool"""
    
    def __init__(self):
        self.name = "clickhouse_query"
        self.description = "Execute SQL queries against ClickHouse database"
        self._query_func = None
    
    async def initialize(self):
        """Initialize the MCP connection"""
        self._query_func = await create_clickhouse_mcp_agent()
        return self._query_func is not None
    
    async def run(self, query: str) -> str:
        """Execute a query"""
        if not self._query_func:
            await self.initialize()
        
        if not self._query_func:
            return "Error: Could not initialize ClickHouse MCP connection"
        
        return await self._query_func(query)


# Synchronous wrapper for compatibility with existing code
class ClickHouseMCPTool:
    """Synchronous wrapper for the async ClickHouse MCP tool"""
    
    def __init__(self):
        self.name = "clickhouse_query"
        self.description = "Execute SQL queries against ClickHouse database"
        self._async_tool = AsyncClickHouseTool()
    
    def _run(self, query: str) -> str:
        """Synchronous interface to async tool"""
        try:
            # Run the async function in an event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(self._async_tool.run(query))
                return result
            finally:
                loop.close()
        except Exception as e:
            return f"Error executing ClickHouse query: {str(e)}"
    
    def run(self, query: str) -> str:
        """Public interface"""
        return self._run(query)


if __name__ == "__main__":
    # Test the implementation
    asyncio.run(test_user_query("0014J00000JAuIGQA1", "מה התורים שלי"))