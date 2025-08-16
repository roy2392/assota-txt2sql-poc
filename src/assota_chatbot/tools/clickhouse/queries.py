"""Predefined ClickHouse queries for common operations"""

from typing import List, Optional
from datetime import datetime, timedelta


class QueryBuilder:
    """Builder for ClickHouse queries with proper user_id filtering"""
    
    TABLE_NAME = "appointments_cleaned_for_bigquery"
    
    @staticmethod
    def validate_user_id(user_id: str) -> None:
        """Validate user_id to prevent SQL injection"""
        if not user_id or not isinstance(user_id, str):
            raise ValueError("User ID must be a non-empty string")
        
        # Basic validation - alphanumeric and common characters
        if not all(c.isalnum() or c in ".-_" for c in user_id):
            raise ValueError("User ID contains invalid characters")
    
    @classmethod
    def get_user_appointments(
        cls, 
        user_id: str, 
        limit: int = 10,
        order_by: str = "appointment_date_time_c DESC"
    ) -> str:
        """Get user appointments with optional limit and ordering"""
        cls.validate_user_id(user_id)
        
        return f"""
        SELECT 
            row_id,
            user_id,
            appoitment_type,
            appointment_date_time_c,
            appointment_status,
            cancel_reason_code,
            record_type,
            site_name,
            site_address,
            site_instructions
        FROM {cls.TABLE_NAME}
        WHERE user_id = '{user_id}'
        ORDER BY {order_by}
        LIMIT {limit}
        """
    
    @classmethod
    def get_upcoming_appointments(cls, user_id: str, days_ahead: int = 30) -> str:
        """Get upcoming appointments for a user"""
        cls.validate_user_id(user_id)
        future_date = (datetime.now() + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
        
        return f"""
        SELECT 
            appoitment_type,
            appointment_date_time_c,
            appointment_status,
            site_name,
            site_address
        FROM {cls.TABLE_NAME}
        WHERE user_id = '{user_id}'
            AND appointment_date_time_c >= now()
            AND appointment_date_time_c <= '{future_date}'
        ORDER BY appointment_date_time_c ASC
        """
    
    @classmethod
    def get_appointment_count(cls, user_id: str) -> str:
        """Get total appointment count for user"""
        cls.validate_user_id(user_id)
        
        return f"""
        SELECT COUNT(*) as total
        FROM {cls.TABLE_NAME}
        WHERE user_id = '{user_id}'
        """
    
    @classmethod
    def get_appointments_by_type(cls, user_id: str) -> str:
        """Get appointment breakdown by type"""
        cls.validate_user_id(user_id)
        
        return f"""
        SELECT 
            appoitment_type,
            COUNT(*) as count,
            MAX(appointment_date_time_c) as last_appointment
        FROM {cls.TABLE_NAME}
        WHERE user_id = '{user_id}'
        GROUP BY appoitment_type
        ORDER BY count DESC
        """
    
    @classmethod
    def get_appointments_by_status(cls, user_id: str) -> str:
        """Get appointment breakdown by status"""
        cls.validate_user_id(user_id)
        
        return f"""
        SELECT 
            appointment_status,
            COUNT(*) as count
        FROM {cls.TABLE_NAME}
        WHERE user_id = '{user_id}'
        GROUP BY appointment_status
        ORDER BY count DESC
        """
    
    @classmethod
    def get_appointments_by_site(cls, user_id: str) -> str:
        """Get appointments breakdown by site"""
        cls.validate_user_id(user_id)
        
        return f"""
        SELECT 
            site_name,
            site_address,
            COUNT(*) as visit_count,
            MAX(appointment_date_time_c) as last_visit
        FROM {cls.TABLE_NAME}
        WHERE user_id = '{user_id}'
        GROUP BY site_name, site_address
        ORDER BY visit_count DESC
        """
    
    @classmethod
    def search_appointments(
        cls, 
        user_id: str, 
        search_term: str, 
        limit: int = 10
    ) -> str:
        """Search appointments by type or site name"""
        cls.validate_user_id(user_id)
        
        # Basic escaping for search term
        search_term = search_term.replace("'", "''")
        
        return f"""
        SELECT 
            appoitment_type,
            appointment_date_time_c,
            appointment_status,
            site_name,
            site_address
        FROM {cls.TABLE_NAME}
        WHERE user_id = '{user_id}'
            AND (
                appoitment_type ILIKE '%{search_term}%'
                OR site_name ILIKE '%{search_term}%'
            )
        ORDER BY appointment_date_time_c DESC
        LIMIT {limit}
        """