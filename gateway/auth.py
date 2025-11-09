"""API key authentication for gateway."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import Optional
from fastapi import HTTPException, Security, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel

from shared.database import get_db
from shared import crud

security = HTTPBearer(auto_error=False)


class APIKeyInfo(BaseModel):
    """API key information after validation."""
    key_id: int
    key: str
    user_id: str
    tier: str


def verify_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
    db: Session = Depends(get_db),
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

    # Look up API key in database
    db_key = crud.get_api_key(db, api_key)

    if not db_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key. Please check your credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if key is active
    if not db_key.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has been deactivated.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check expiration
    if db_key.expires_at and db_key.expires_at < db_key.updated_at:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return APIKeyInfo(
        key_id=db_key.id,
        key=db_key.key,
        user_id=db_key.user_id,
        tier=db_key.tier,
    )
