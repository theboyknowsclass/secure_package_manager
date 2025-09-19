"""Database operations for AuditLog entities."""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from ..models import AuditLog
from .base_operations import BaseOperations

class AuditLogOperations(BaseOperations):
    """Database operations for AuditLog entities."""
    
    def log_action(self, user_id: int, action: str, resource_type: str, 
                   resource_id: Optional[int] = None, details: Optional[str] = None) -> AuditLog:
        """Log an audit action.
        
        Args:
            user_id: The ID of the user performing the action
            action: The action being performed
            resource_type: The type of resource being acted upon
            resource_id: The ID of the resource (optional)
            details: Additional details about the action (optional)
            
        Returns:
            The created audit log entry
        """
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details
        )
        self.session.add(audit_log)
        return audit_log
    
    def get_by_user(self, user_id: int) -> List[AuditLog]:
        """Get audit logs by user.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            List of audit logs for the specified user
        """
        stmt = select(AuditLog).where(AuditLog.user_id == user_id)
        return list(self.session.execute(stmt).scalars().all())
    
    def get_by_resource(self, resource_type: str, resource_id: int) -> List[AuditLog]:
        """Get audit logs by resource.
        
        Args:
            resource_type: The type of resource
            resource_id: The ID of the resource
            
        Returns:
            List of audit logs for the specified resource
        """
        stmt = select(AuditLog).where(
            and_(
                AuditLog.resource_type == resource_type,
                AuditLog.resource_id == resource_id
            )
        )
        return list(self.session.execute(stmt).scalars().all())
    
    def get_all(self) -> List[AuditLog]:
        """Get all audit logs.
        
        Returns:
            List of all audit logs
        """
        return super().get_all(AuditLog)
