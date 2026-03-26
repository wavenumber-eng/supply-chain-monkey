"""Bearer token authentication dependency."""

from fastapi import Header, HTTPException

from .settings import settings


async def verify_token(authorization: str = Header()) -> str:
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

    token = authorization[len(prefix):]
    if token != settings.service_token:
        raise HTTPException(status_code=401, detail="Invalid or missing token")

    return token
