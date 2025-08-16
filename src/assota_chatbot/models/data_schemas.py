"""Pydantic schemas for data validation"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class AppointmentRecord(BaseModel):
    """Schema for appointment data from ClickHouse"""
    
    row_id: str
    user_id: str
    appointment_type: str = Field(alias="appoitment_type")  # Note: DB has typo
    appointment_date_time: datetime = Field(alias="appointment_date_time_c")
    appointment_status: str
    cancel_reason_code: Optional[float] = None
    record_type: str
    site_name: str
    site_address: str
    site_instructions: Optional[str] = None
    
    class Config:
        allow_population_by_field_name = True


class UserQuery(BaseModel):
    """Schema for user input validation"""
    
    user_id: str = Field(..., min_length=1, description="User identifier")
    query: str = Field(..., min_length=1, max_length=1000, description="User question")
    language: str = Field(default="he", description="Response language")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")


class AgentResponse(BaseModel):
    """Schema for agent response"""
    
    answer: str = Field(..., description="Agent's response")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Response confidence")
    query_type: str = Field(..., description="Type of query processed")
    data_sources: List[str] = Field(default_factory=list, description="Data sources used")
    execution_time: Optional[float] = Field(default=None, description="Processing time in seconds")
    
    
class SQLQueryResult(BaseModel):
    """Schema for SQL query results"""
    
    columns: List[str]
    rows: List[List[Any]]
    query: str
    execution_time: Optional[float] = None
    record_count: int
    
    @property
    def as_dict_list(self) -> List[Dict[str, Any]]:
        """Convert rows to list of dictionaries"""
        return [dict(zip(self.columns, row)) for row in self.rows]


class ErrorResponse(BaseModel):
    """Schema for error responses"""
    
    error_type: str = Field(..., description="Type of error")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.now)
    user_id: Optional[str] = Field(default=None, description="User associated with error")