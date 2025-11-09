"""API key authentication middleware."""
from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .config import config, APIKeyInfo


security = HTTPBearer(auto_error=False)


def verify_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> APIKeyInfo:
    """
    Verify API key from Authorization header.

    Expected format: "Bearer sk-internal-xxx"

    Returns:
        APIKeyInfo: Information about the authenticated user

    Raises:
        HTTPException: If authentication fails
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Please provide a valid API key in the Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    api_key = credentials.credentials

    # Look up API key in configuration
    if api_key not in config.api_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key. Please check your credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return config.api_keys[api_key]


def get_api_key_from_header(auth_header: Optional[str]) -> Optional[str]:
    """Extract API key from Authorization header."""
    if not auth_header:
        return None

    if config.security.use_bearer_format:
        if auth_header.startswith("Bearer "):
            return auth_header[7:]  # Remove "Bearer " prefix
        return None

    return auth_header
