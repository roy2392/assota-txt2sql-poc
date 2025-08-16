"""ClickHouse MCP client for database operations"""

import asyncio
import logging
from typing import Optional, Dict, Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ...config.settings import settings
from ...models.data_schemas import SQLQueryResult

logger = logging.getLogger(__name__)


class ClickHouseMCPClient:
    """Async ClickHouse MCP client"""
    
    def __init__(self):
        self._session: Optional[ClientSession] = None
        self._server_params = self._create_server_params()
    
    def _create_server_params(self) -> StdioServerParameters:
        """Create MCP server parameters from settings"""
        env = {
            "CLICKHOUSE_HOST": settings.clickhouse.host,
            "CLICKHOUSE_PORT": str(settings.clickhouse.port),
            "CLICKHOUSE_USER": settings.clickhouse.user,
            "CLICKHOUSE_PASSWORD": settings.clickhouse.password,
            "CLICKHOUSE_SECURE": str(settings.clickhouse.secure).lower(),
            "CLICKHOUSE_VERIFY": str(settings.clickhouse.verify).lower(),
            "CLICKHOUSE_CONNECT_TIMEOUT": str(settings.clickhouse.connect_timeout),
            "CLICKHOUSE_SEND_RECEIVE_TIMEOUT": str(settings.clickhouse.send_receive_timeout)
        }
        
        return StdioServerParameters(
            command="uv",
            args=["run", "--with", "mcp-clickhouse", "--python", "3.11", "mcp-clickhouse"],
            env=env
        )
    
    async def execute_query(self, query: str) -> SQLQueryResult:
        """Execute a SELECT query and return structured results"""
        try:
            async with stdio_client(self._server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    logger.info(f"Executing ClickHouse query: {query[:100]}...")
                    result = await session.call_tool("run_select_query", {"query": query})
                    
                    if result.content and len(result.content) > 0:
                        content = result.content[0]
                        
                        # Handle structured content
                        if hasattr(result, 'structuredContent') and result.structuredContent:
                            data = result.structuredContent
                            return SQLQueryResult(
                                columns=data.get('columns', []),
                                rows=data.get('rows', []),
                                query=query,
                                record_count=len(data.get('rows', []))
                            )
                        
                        # Handle text content
                        if hasattr(content, 'text'):
                            import json
                            try:
                                data = json.loads(content.text)
                                return SQLQueryResult(
                                    columns=data.get('columns', []),
                                    rows=data.get('rows', []),
                                    query=query,
                                    record_count=len(data.get('rows', []))
                                )
                            except json.JSONDecodeError:
                                logger.error(f"Failed to parse JSON response: {content.text}")
                                raise ValueError("Invalid JSON response from ClickHouse")
                        
                        return SQLQueryResult(
                            columns=[],
                            rows=[],
                            query=query,
                            record_count=0
                        )
                    else:
                        logger.warning("No content in ClickHouse response")
                        return SQLQueryResult(
                            columns=[],
                            rows=[],
                            query=query,
                            record_count=0
                        )
                        
        except Exception as e:
            logger.error(f"ClickHouse query failed: {str(e)}")
            raise
    
    async def test_connection(self) -> bool:
        """Test ClickHouse connection"""
        try:
            result = await self.execute_query("SELECT 1 as test")
            return result.record_count > 0
        except Exception as e:
            logger.error(f"ClickHouse connection test failed: {str(e)}")
            return False
    
    async def get_user_appointment_count(self, user_id: str) -> int:
        """Get total appointment count for a user"""
        try:
            query = f"SELECT COUNT(*) as total FROM appointments_cleaned_for_bigquery WHERE user_id = '{user_id}'"
            result = await self.execute_query(query)
            
            if result.record_count > 0 and result.rows:
                return int(result.rows[0][0])
            return 0
        except Exception as e:
            logger.error(f"Failed to get appointment count for user {user_id}: {str(e)}")
            return 0


# Global client instance
clickhouse_client = ClickHouseMCPClient()