"""Bearer token authentication dependency and HTTP error metadata."""

from typing import Annotated

from fastapi import Header, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from scm.models import HttpErrorDetail, ValidationErrorDetail

from .settings import settings


bearer_scheme = HTTPBearer(auto_error=False, scheme_name="BearerAuth")

CONTRACT_ERROR_RESPONSES = {
    401: {"model": HttpErrorDetail, "description": "Access is unauthorized."},
    422: {"model": ValidationErrorDetail, "description": "Client error"},
    500: {"model": HttpErrorDetail, "description": "Server error"},
}


async def verify_token(
    authorization: Annotated[str, Header(include_in_schema=False)],
    _security_metadata: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(bearer_scheme),
    ],
) -> str:
    """Validate the bearer token from the Authorization header.

    Returns the token on success, raises 401 on failure.
    """
    if not settings.service_token:
        raise HTTPException(
            status_code=500,
            detail="Service token not configured",
        )

    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise HTTPException(status_code=401, detail="Invalid or missing token")

    token = authorization[len(prefix) :]
    if token != settings.service_token:
        raise HTTPException(status_code=401, detail="Invalid or missing token")

    return token
