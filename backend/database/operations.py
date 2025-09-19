"""
Database Operations - Shared operations for both Flask-SQLAlchemy and pure SQLAlchemy
Abstracts common database patterns used across API and workers
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DatabaseOperations:
    """
    Shared database operations that work with both Flask-SQLAlchemy and pure SQLAlchemy
    """

    def __init__(self, session_or_db):
        """
        Initialize with either Flask-SQLAlchemy db or pure SQLAlchemy session

        Args:
            session_or_db: Either Flask-SQLAlchemy db object or SQLAlchemy session
        """
        self.session_or_db = session_or_db
        self.is_flask_sqlalchemy = hasattr(session_or_db, "session")

    def _get_session(self):
        """Get the appropriate session object"""
        if self.is_flask_sqlalchemy:
            return self.session_or_db.session
        return self.session_or_db

    def _get_query(self, model_class):
        """Get the appropriate query object"""
        if self.is_flask_sqlalchemy:
            return model_class.query
        else:
            from sqlalchemy import select

            return select(model_class)

    # ===== PACKAGE OPERATIONS =====

    def get_package_by_id(self, package_id: int, model_class) -> Optional[Any]:
        """Get package by ID"""
        try:
            if self.is_flask_sqlalchemy:
                return model_class.query.get(package_id)
            else:
                session = self._get_session()
                return session.get(model_class, package_id)
        except Exception as e:
            logger.error(f"Error getting package {package_id}: {str(e)}")
            return None

    def get_package_or_404(self, package_id: int, model_class):
        """Get package by ID or raise 404 (Flask-SQLAlchemy style)"""
        if self.is_flask_sqlalchemy:
            return model_class.query.get_or_404(package_id)
        else:
            package = self.get_package_by_id(package_id, model_class)
            if not package:
                from werkzeug.exceptions import NotFound

                raise NotFound(f"Package {package_id} not found")
            return package

    def get_packages_by_status(self, status: str, model_class, status_model_class) -> List[Any]:
        """Get packages by status"""
        try:
            if self.is_flask_sqlalchemy:
                return model_class.query.join(status_model_class).filter(status_model_class.status == status).all()
            else:
                session = self._get_session()
                from sqlalchemy import select

                return (
                    session.execute(
                        select(model_class).join(status_model_class).where(status_model_class.status == status)
                    )
                    .scalars()
                    .all()
                )
        except Exception as e:
            logger.error(f"Error getting packages by status {status}: {str(e)}")
            return []

    def get_packages_by_statuses(self, statuses: List[str], model_class, status_model_class) -> List[Any]:
        """Get packages by multiple statuses"""
        try:
            if self.is_flask_sqlalchemy:
                return model_class.query.join(status_model_class).filter(status_model_class.status.in_(statuses)).all()
            else:
                session = self._get_session()
                from sqlalchemy import select

                return (
                    session.execute(
                        select(model_class).join(status_model_class).where(status_model_class.status.in_(statuses))
                    )
                    .scalars()
                    .all()
                )
        except Exception as e:
            logger.error(f"Error getting packages by statuses {statuses}: {str(e)}")
            return []

    def create_package(self, package_data: Dict[str, Any], model_class) -> Any:
        """Create a new package"""
        try:
            package = model_class(**package_data)
            session = self._get_session()
            session.add(package)
            session.flush()  # Get the ID
            return package
        except Exception as e:
            logger.error(f"Error creating package: {str(e)}")
            raise

    def update_package_status(self, package_id: int, new_status: str, status_model_class, **kwargs) -> bool:
        """Update package status"""
        try:
            session = self._get_session()

            if self.is_flask_sqlalchemy:
                status = session.query(status_model_class).filter_by(package_id=package_id).first()
            else:
                from sqlalchemy import select

                result = session.execute(select(status_model_class).where(status_model_class.package_id == package_id))
                status = result.scalar_one_or_none()

            if not status:
                logger.warning(f"No status found for package {package_id}")
                return False

            # Update status and any additional fields
            status.status = new_status
            status.updated_at = datetime.utcnow()

            for key, value in kwargs.items():
                if hasattr(status, key):
                    setattr(status, key, value)

            session.commit()
            logger.info(f"Updated package {package_id} status to {new_status}")
            return True

        except Exception as e:
            logger.error(f"Error updating package {package_id} status: {str(e)}")
            session.rollback()
            return False

    def advance_package_status(self, package_id: int, next_status: str, status_model_class) -> bool:
        """Advance package to next status (alias for update_package_status)"""
        return self.update_package_status(package_id, next_status, status_model_class)

    # ===== REQUEST OPERATIONS =====

    def get_request_by_id(self, request_id: int, model_class) -> Optional[Any]:
        """Get request by ID"""
        try:
            if self.is_flask_sqlalchemy:
                return model_class.query.get(request_id)
            else:
                session = self._get_session()
                return session.get(model_class, request_id)
        except Exception as e:
            logger.error(f"Error getting request {request_id}: {str(e)}")
            return None

    def create_request(self, request_data: Dict[str, Any], model_class) -> Any:
        """Create a new request"""
        try:
            request = model_class(**request_data)
            session = self._get_session()
            session.add(request)
            session.flush()  # Get the ID
            return request
        except Exception as e:
            logger.error(f"Error creating request: {str(e)}")
            raise

    # ===== BATCH OPERATIONS =====

    def create_package_records(
        self,
        packages_data: List[Dict[str, Any]],
        request_id: int,
        package_model_class,
        status_model_class,
        request_package_model_class,
    ) -> List[Any]:
        """Create multiple package records with status and request links"""
        try:
            session = self._get_session()
            package_objects = []

            for package_data in packages_data:
                # Create package
                package = package_model_class(**package_data)
                session.add(package)
                session.flush()  # Get the package ID

                # Create package status
                package_status = status_model_class(
                    package_id=package.id, status="Submitted", security_scan_status="pending"
                )
                session.add(package_status)

                # Create request-package link
                request_package = request_package_model_class(
                    request_id=request_id, package_id=package.id, package_type="new"
                )
                session.add(request_package)

                package_objects.append(package)
                logger.info(f"Created package: {package.name}@{package.version}")

            session.commit()
            return package_objects

        except Exception as e:
            logger.error(f"Error creating package records: {str(e)}")
            session.rollback()
            raise

    # ===== AUDIT OPERATIONS =====

    def log_action(
        self, user_id: int, action: str, resource_type: str, resource_id: int, details: str, audit_model_class
    ) -> bool:
        """Log an audit action"""
        try:
            audit_log = audit_model_class(
                user_id=user_id, action=action, resource_type=resource_type, resource_id=resource_id, details=details
            )
            session = self._get_session()
            session.add(audit_log)
            session.commit()
            return True
        except Exception as e:
            logger.error(f"Error logging action: {str(e)}")
            session.rollback()
            return False

    # ===== QUERY HELPERS =====

    def count_packages_by_status(self, status: str, package_model_class, status_model_class) -> int:
        """Count packages by status"""
        try:
            if self.is_flask_sqlalchemy:
                return (
                    package_model_class.query.join(status_model_class)
                    .filter(status_model_class.status == status)
                    .count()
                )
            else:
                session = self._get_session()
                from sqlalchemy import func, select

                result = session.execute(
                    select(func.count(package_model_class.id))
                    .join(status_model_class)
                    .where(status_model_class.status == status)
                )
                return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error counting packages by status {status}: {str(e)}")
            return 0

    def get_pending_requests(self, request_model_class) -> List[Any]:
        """Get requests that need processing"""
        try:
            if self.is_flask_sqlalchemy:
                return request_model_class.query.all()
            else:
                session = self._get_session()
                from sqlalchemy import select

                return session.execute(select(request_model_class)).scalars().all()
        except Exception as e:
            logger.error(f"Error getting pending requests: {str(e)}")
            return []

    def get_package_by_name_version(self, name: str, version: str, package_model_class) -> Optional[Any]:
        """Get package by name and version"""
        try:
            if self.is_flask_sqlalchemy:
                return package_model_class.query.filter_by(name=name, version=version).first()
            else:
                session = self._get_session()
                from sqlalchemy import select

                result = session.execute(
                    select(package_model_class).where(
                        package_model_class.name == name, package_model_class.version == version
                    )
                )
                return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting package by name/version: {str(e)}")
            return None

    def get_request_package_link(self, request_id: int, package_id: int, request_package_model_class) -> Optional[Any]:
        """Get request-package link"""
        try:
            if self.is_flask_sqlalchemy:
                return request_package_model_class.query.filter_by(request_id=request_id, package_id=package_id).first()
            else:
                session = self._get_session()
                from sqlalchemy import select

                result = session.execute(
                    select(request_package_model_class).where(
                        request_package_model_class.request_id == request_id,
                        request_package_model_class.package_id == package_id,
                    )
                )
                return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting request-package link: {str(e)}")
            return None

    def create_request_package_link(
        self, request_id: int, package_id: int, package_type: str, request_package_model_class
    ) -> bool:
        """Create request-package link"""
        try:
            request_package = request_package_model_class(
                request_id=request_id, package_id=package_id, package_type=package_type
            )
            session = self._get_session()
            session.add(request_package)
            session.commit()
            return True
        except Exception as e:
            logger.error(f"Error creating request-package link: {str(e)}")
            session.rollback()
            return False

    # ===== USER OPERATIONS =====

    def get_user_by_username(self, username: str, model_class) -> Optional[Any]:
        """Get user by username"""
        try:
            if self.is_flask_sqlalchemy:
                return model_class.query.filter_by(username=username).first()
            else:
                from sqlalchemy import select

                session = self._get_session()
                stmt = select(model_class).where(model_class.username == username)
                return session.execute(stmt).scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user by username {username}: {str(e)}")
            return None

    def get_user_by_id(self, user_id: int, model_class) -> Optional[Any]:
        """Get user by ID"""
        try:
            if self.is_flask_sqlalchemy:
                return model_class.query.get(user_id)
            else:
                from sqlalchemy import select

                session = self._get_session()
                stmt = select(model_class).where(model_class.id == user_id)
                return session.execute(stmt).scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {str(e)}")
            return None

    def create_user(self, user_data: Dict[str, Any], model_class) -> Optional[Any]:
        """Create a new user"""
        try:
            session = self._get_session()
            user = model_class(**user_data)
            session.add(user)
            session.commit()
            session.refresh(user)
            logger.info(f"Created user: {user.username}")
            return user
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            session.rollback()
            return None

    def update_user(self, user: Any, update_data: Dict[str, Any]) -> bool:
        """Update an existing user"""
        try:
            session = self._get_session()
            for key, value in update_data.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            session.commit()
            logger.info(f"Updated user: {user.username}")
            return True
        except Exception as e:
            logger.error(f"Error updating user {user.username}: {str(e)}")
            session.rollback()
            return False

    # ===== BASIC SESSION OPERATIONS =====

    def add(self, obj: Any) -> None:
        """Add an object to the session"""
        session = self._get_session()
        session.add(obj)

    def commit(self) -> None:
        """Commit the current transaction"""
        session = self._get_session()
        session.commit()

    def rollback(self) -> None:
        """Rollback the current transaction"""
        session = self._get_session()
        session.rollback()

    def delete(self, obj: Any) -> None:
        """Delete an object from the session"""
        session = self._get_session()
        session.delete(obj)

    def query(self, *entities):
        """Create a query object"""
        if self.is_flask_sqlalchemy:
            # For Flask-SQLAlchemy, we need to use the model's query attribute
            if len(entities) == 1:
                return entities[0].query
            else:
                # Multi-entity query - use session.query
                session = self._get_session()
                return session.query(*entities)
        else:
            # For pure SQLAlchemy, use session.query
            session = self._get_session()
            return session.query(*entities)
