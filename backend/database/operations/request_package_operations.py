"""Database operations for RequestPackage entities."""

from typing import List

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from ..models import RequestPackage


class RequestPackageOperations:
    """Database operations for RequestPackage entities."""

    def get_by_request_id(self, request_id: int) -> List[RequestPackage]:
        """Get all request-package links for a request.

        Args:
            request_id: The ID of the request

        Returns:
            List of request-package links for the specified request
        """
        stmt = select(RequestPackage).where(RequestPackage.request_id == request_id)
        return list(self.session.execute(stmt).scalars().all())

    def get_by_package_id(self, package_id: int) -> List[RequestPackage]:
        """Get all request-package links for a package.

        Args:
            package_id: The ID of the package

        Returns:
            List of request-package links for the specified package
        """
        stmt = select(RequestPackage).where(RequestPackage.package_id == package_id)
        return list(self.session.execute(stmt).scalars().all())

    def link_exists(self, request_id: int, package_id: int) -> bool:
        """Check if request-package link exists.

        Args:
            request_id: The ID of the request
            package_id: The ID of the package

        Returns:
            True if the link exists, False otherwise
        """
        stmt = select(RequestPackage).where(
            and_(
                RequestPackage.request_id == request_id,
                RequestPackage.package_id == package_id,
            )
        )
        return self.session.execute(stmt).scalar_one_or_none() is not None

    def __init__(self, session: Session):
        """Initialize with a database session.

        Args:
            session: SQLAlchemy session for database operations
        """
        self.session = session

    def create_link(self, request_id: int, package_id: int, package_type: str = "new") -> RequestPackage:
        """Create a request-package link.

        Args:
            request_id: The ID of the request
            package_id: The ID of the package
            package_type: Type of package ("new" or "existing")

        Returns:
            The created request-package link
        """
        link = RequestPackage(
            request_id=request_id,
            package_id=package_id,
            package_type=package_type,
        )
        self.session.add(link)
        return link

    def get_all(self) -> List[RequestPackage]:
        """Get all request-package links.

        Returns:
            List of all request-package links
        """
        return list(self.session.query(RequestPackage).all())

    def get_all_for_request(self, request_id: int) -> List[RequestPackage]:
        """Get all request-package links for a specific request.

        Args:
            request_id: The ID of the request

        Returns:
            List of all request-package links for the specified request
        """
        return list(self.session.query(RequestPackage).filter(RequestPackage.request_id == request_id).all())

    def check_user_access(self, package_id: int, user_id: int) -> bool:
        """Check if user has access to a package through any request.

        Args:
            package_id: The ID of the package
            user_id: The ID of the user

        Returns:
            True if user has access, False otherwise
        """
        from ..models import Request

        stmt = (
            select(RequestPackage)
            .join(Request)
            .where(
                and_(
                    RequestPackage.package_id == package_id,
                    Request.requestor_id == user_id,
                )
            )
        )
        return self.session.execute(stmt).scalar_one_or_none() is not None
