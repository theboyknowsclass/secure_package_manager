"""Database operations for Request entities."""

from typing import List, Optional, Type

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from ..models import Request, RequestPackage
from .base_operations import BaseOperations


class RequestOperations(BaseOperations):
    """Database operations for Request entities."""

    def get_needing_parsing(self) -> List[Request]:
        """Get requests that need package parsing.

        Returns requests that have raw_request_blob but no associated packages yet.

        Returns:
            List of requests that need parsing
        """
        stmt = select(Request).where(
            and_(
                Request.raw_request_blob.isnot(None),
                ~Request.id.in_(select(RequestPackage.request_id).distinct()),
            )
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_by_requestor(self, requestor_id: int) -> List[Request]:
        """Get requests by requestor ID.

        Args:
            requestor_id: The ID of the user who made the requests

        Returns:
            List of requests made by the specified user
        """
        stmt = select(Request).where(Request.requestor_id == requestor_id)
        return list(self.session.execute(stmt).scalars().all())

    def get_with_packages(self, request_id: int) -> Optional[Request]:
        """Get request with all associated packages.

        Args:
            request_id: The ID of the request

        Returns:
            The request if found, None otherwise
        """
        stmt = select(Request).where(Request.id == request_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_all(self, model_class: Type[Request]) -> List[Request]:
        """Get all requests.

        Returns:
            List of all requests
        """
        return super().get_all(Request)

    def get_by_id(self, request_id: int) -> Optional[Request]:
        """Get request by ID.

        Args:
            request_id: The ID of the request

        Returns:
            The request if found, None otherwise
        """
        return super().get_by_id(Request, request_id)

    def count_total_requests(self) -> int:
        """Count total number of requests.

        Returns:
            Total number of requests
        """
        stmt = select(Request)
        return self.session.execute(stmt).scalars().count()

    def get_with_packages_and_status(
        self, request_id: int
    ) -> Optional[Request]:
        """Get request with all associated packages and their statuses.

        Args:
            request_id: The ID of the request

        Returns:
            The request with packages and statuses if found, None otherwise
        """
        from ..models import PackageStatus

        stmt = (
            select(Request)
            .join(RequestPackage)
            .join(PackageStatus)
            .where(Request.id == request_id)
        )
        return self.session.execute(stmt).scalar_one_or_none()
