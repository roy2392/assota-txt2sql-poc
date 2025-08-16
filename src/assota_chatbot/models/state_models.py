"""State management for the React Agent"""

from typing import List, Dict, Any, Optional
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage


class ReactAgentState(TypedDict):
    """State for React agent workflow"""
    
    # Input/Output
    messages: List[BaseMessage]
    user_input: str
    user_id: str
    final_answer: str
    
    # React process
    thought: str
    action: str
    action_input: str
    observation: str
    
    # Control flow
    iteration: int
    max_iterations: Optional[int]
    current_step: str
    
    # Context
    user_data: Optional[List[Dict[str, Any]]]
    context: Optional[Dict[str, Any]]


class ConversationState(TypedDict):
    """Extended state for conversation management"""
    
    # Session management
    session_id: str
    user_profile: Optional[Dict[str, Any]]
    conversation_history: List[Dict[str, Any]]
    
    # Language and locale
    language: str
    locale: str
    
    # System state
    error_count: int
    last_activity: Optional[str]