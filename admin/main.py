"""Admin API service for managing API keys and users."""
import sys
import os
from pathlib import Path

# Add parent directory to path for shared imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import secrets
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from shared.database import get_db, init_db
from shared.models import APIKey, RequestLog
from shared import crud
from shared.config import settings
from shared.email_service import get_email_service
import random

app = FastAPI(title="LLM API Admin Service", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()


# Pydantic models
class APIKeyCreate(BaseModel):
    user_id: str
    tier: str = "standard"
    description: Optional[str] = None
    expires_in_days: Optional[int] = None


class APIKeyUpdate(BaseModel):
    tier: Optional[str] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None


class APIKeyResponse(BaseModel):
    id: int
    key: str
    user_id: str
    tier: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime]
    description: Optional[str]
    created_by: Optional[str]

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# Self-service auth models
class EmailRequest(BaseModel):
    email: str


class VerifyCodeRequest(BaseModel):
    email: str
    code: str


class APIKeySuccessResponse(BaseModel):
    api_key: str
    message: str


class UsageStats(BaseModel):
    date: str
    requests: int
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int


# Authentication
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.admin_token_expire_minutes)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.admin_secret_key, algorithm=settings.admin_algorithm)
    return encoded_jwt


def verify_admin_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """Verify admin JWT token."""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, settings.admin_secret_key, algorithms=[settings.admin_algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")

        admin = crud.get_admin_user(db, username)
        if admin is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")

        return admin
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")


# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database and create default admin user."""
    init_db()

    # Create default admin user if not exists
    db = next(get_db())
    admin = crud.get_admin_user(db, "admin")
    if not admin:
        crud.create_admin_user(db, username="admin", password="admin123", email="admin@localhost")
        print("Default admin user created: username=admin, password=admin123")
        print("PLEASE CHANGE THE DEFAULT PASSWORD!")


# Routes
@app.post("/api/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Admin login."""
    admin = crud.get_admin_user(db, request.username)
    if not admin or not crud.verify_admin_password(request.password, admin.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    # Update last login
    crud.update_admin_last_login(db, admin.id)

    # Create access token
    access_token = create_access_token(data={"sub": admin.username})
    return TokenResponse(access_token=access_token)


@app.get("/api/keys", response_model=List[APIKeyResponse])
async def list_keys(
    skip: int = 0,
    limit: int = 100,
    admin=Depends(verify_admin_token),
    db: Session = Depends(get_db),
):
    """List all API keys."""
    keys = crud.list_api_keys(db, skip=skip, limit=limit)
    return keys


@app.post("/api/keys", response_model=APIKeyResponse)
async def create_key(
    key_data: APIKeyCreate,
    admin=Depends(verify_admin_token),
    db: Session = Depends(get_db),
):
    """Create a new API key."""
    # Generate random API key
    new_key = f"sk-internal-{secrets.token_urlsafe(32)}"

    # Check tier validity
    if key_data.tier not in ["free", "standard", "premium"]:
        raise HTTPException(status_code=400, detail="Invalid tier. Must be free, standard, or premium")

    # Calculate expiration
    expires_at = None
    if key_data.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=key_data.expires_in_days)

    # Create key
    api_key = crud.create_api_key(
        db,
        key=new_key,
        user_id=key_data.user_id,
        tier=key_data.tier,
        description=key_data.description,
        created_by=admin.username,
        expires_at=expires_at,
    )

    return api_key


@app.put("/api/keys/{key_id}", response_model=APIKeyResponse)
async def update_key(
    key_id: int,
    key_data: APIKeyUpdate,
    admin=Depends(verify_admin_token),
    db: Session = Depends(get_db),
):
    """Update an API key."""
    updated_key = crud.update_api_key(
        db,
        key_id=key_id,
        tier=key_data.tier,
        is_active=key_data.is_active,
        description=key_data.description,
    )

    if not updated_key:
        raise HTTPException(status_code=404, detail="API key not found")

    return updated_key


@app.delete("/api/keys/{key_id}")
async def delete_key(
    key_id: int,
    admin=Depends(verify_admin_token),
    db: Session = Depends(get_db),
):
    """Delete (deactivate) an API key."""
    success = crud.delete_api_key(db, key_id)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")

    return {"message": "API key deleted successfully"}


@app.get("/api/usage", response_model=List[UsageStats])
async def get_usage(
    user_id: Optional[str] = None,
    days: int = 7,
    admin=Depends(verify_admin_token),
    db: Session = Depends(get_db),
):
    """Get usage statistics."""
    stats = crud.get_usage_stats(db, user_id=user_id, days=days)

    return [
        UsageStats(
            date=str(stat.date),
            requests=stat.requests or 0,
            total_tokens=stat.total_tokens or 0,
            prompt_tokens=stat.prompt_tokens or 0,
            completion_tokens=stat.completion_tokens or 0,
        )
        for stat in stats
    ]


# ============================================================================
# Self-Service Auth API (for users to get their own API keys via email)
# ============================================================================

@app.post("/auth/request-code")
async def request_verification_code(
    request: EmailRequest,
    db: Session = Depends(get_db),
):
    """
    Request a verification code via email.

    Users enter their company email and receive a 6-digit code.
    """
    email = request.email.lower().strip()

    # Validate email format
    if "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email format")

    # Check if email domain is allowed
    domain = email.split("@")[1]
    if domain not in settings.allowed_email_domains:
        raise HTTPException(
            status_code=400,
            detail=f"Email domain not allowed. Please use a company email address."
        )

    # Generate 6-digit code
    code = f"{random.randint(100000, 999999)}"

    # Calculate expiration
    expires_at = datetime.utcnow() + timedelta(minutes=settings.verification_code_expire_minutes)

    # Save to database
    crud.create_verification_code(
        db,
        email=email,
        code=code,
        expires_at=expires_at,
    )

    # Send email
    email_service = get_email_service()
    success = email_service.send_verification_code(email, code)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to send verification email")

    # Clean up old expired codes (background task simulation)
    crud.cleanup_expired_codes(db)

    return {
        "message": "Verification code sent to your email",
        "expires_in_minutes": settings.verification_code_expire_minutes
    }


@app.post("/auth/verify-code", response_model=APIKeySuccessResponse)
async def verify_code_and_get_api_key(
    request: VerifyCodeRequest,
    db: Session = Depends(get_db),
):
    """
    Verify the code and issue an API key.

    If the code is valid, automatically create an API key for the user.
    """
    email = request.email.lower().strip()
    code = request.code.strip()

    # Find valid verification code
    verification = crud.get_valid_verification_code(db, email, code)

    if not verification:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired verification code"
        )

    # Mark code as used
    crud.mark_verification_code_used(db, verification.id)

    # Check if user already has an API key
    existing_keys = crud.get_api_keys_by_user(db, email)
    active_keys = [k for k in existing_keys if k.is_active]

    if active_keys:
        # Return existing active key
        return APIKeySuccessResponse(
            api_key=active_keys[0].key,
            message="You already have an active API key"
        )

    # Generate new API key
    new_key = f"sk-internal-{secrets.token_urlsafe(32)}"

    # Create API key with standard tier
    api_key = crud.create_api_key(
        db,
        key=new_key,
        user_id=email,
        tier="standard",
        description="Self-service registration",
        created_by="self-service",
    )

    return APIKeySuccessResponse(
        api_key=api_key.key,
        message="API key created successfully! Please save this key, it won't be shown again."
    )


@app.get("/auth/my-keys", response_model=List[APIKeyResponse])
async def get_my_keys(
    email: str,
    db: Session = Depends(get_db),
):
    """
    Get all API keys for a specific user (by email).

    Note: In production, this should require authentication.
    For now, we just check by email.
    """
    email = email.lower().strip()

    # Validate email domain
    if "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email format")

    domain = email.split("@")[1]
    if domain not in settings.allowed_email_domains:
        raise HTTPException(status_code=400, detail="Email domain not allowed")

    keys = crud.get_api_keys_by_user(db, email)
    return keys


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy", "service": "admin"}


# Serve static files (UI) - mount at the end
ui_dir = Path(__file__).parent / "ui"
if ui_dir.exists():
    app.mount("/", StaticFiles(directory=str(ui_dir), html=True), name="ui")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.admin_host, port=settings.admin_port)
