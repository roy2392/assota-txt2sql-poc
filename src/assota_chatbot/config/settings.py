"""Configuration settings for Assota Medical Chatbot"""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class ClickHouseSettings(BaseSettings):
    """ClickHouse database configuration"""
    
    host: str = Field(default="", env="CLICKHOUSE_HOST")
    port: int = Field(default=8443, env="CLICKHOUSE_PORT")
    user: str = Field(default="default", env="CLICKHOUSE_USER")
    password: str = Field(default="", env="CLICKHOUSE_PASSWORD")
    secure: bool = Field(default=True, env="CLICKHOUSE_SECURE")
    verify: bool = Field(default=True, env="CLICKHOUSE_VERIFY")
    connect_timeout: int = Field(default=30, env="CLICKHOUSE_CONNECT_TIMEOUT")
    send_receive_timeout: int = Field(default=30, env="CLICKHOUSE_SEND_RECEIVE_TIMEOUT")
    
    class Config:
        env_prefix = "CLICKHOUSE_"


class OpenAISettings(BaseSettings):
    """OpenAI API configuration"""
    
    api_key: str = Field(default="", env="OPENAI_API_KEY")
    model: str = Field(default="gpt-4o-mini")
    temperature: float = Field(default=0.1)
    max_tokens: Optional[int] = Field(default=None)
    
    class Config:
        env_prefix = "OPENAI_"


class LangSmithSettings(BaseSettings):
    """LangSmith tracing configuration"""
    
    api_key: Optional[str] = Field(default=None, env="LANGSMITH_API_KEY")
    project: str = Field(default="assota-txt2sql-poc", env="LANGCHAIN_PROJECT")
    tracing_enabled: bool = Field(default=False, env="LANGCHAIN_TRACING_V2")
    endpoint: str = Field(default="https://api.smith.langchain.com", env="LANGCHAIN_ENDPOINT")
    
    class Config:
        env_prefix = "LANGSMITH_"


class AgentSettings(BaseSettings):
    """Agent configuration"""
    
    max_iterations: int = Field(default=3)
    timeout_seconds: int = Field(default=60)
    hebrew_responses: bool = Field(default=True)
    
    class Config:
        env_prefix = "AGENT_"


class AppSettings(BaseSettings):
    """Main application settings"""
    
    debug: bool = Field(default=False, env="DEBUG")
    host: str = Field(default="127.0.0.1", env="HOST")
    port: int = Field(default=5000, env="PORT")
    
    # Sub-configurations
    clickhouse: ClickHouseSettings = ClickHouseSettings()
    openai: OpenAISettings = OpenAISettings()
    langsmith: LangSmithSettings = LangSmithSettings()
    agent: AgentSettings = AgentSettings()
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


# Global settings instance
settings = AppSettings()