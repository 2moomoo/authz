"""CRUD operations for database models."""
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from passlib.context import CryptContext

from .models import APIKey, User, RequestLog, AdminUser, VerificationCode

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# API Key CRUD
def create_api_key(
    db: Session,
    key: str,
    user_id: str,
    tier: str = "standard",
    description: Optional[str] = None,
    created_by: Optional[str] = None,
    expires_at: Optional[datetime] = None,
) -> APIKey:
    """Create a new API key."""
    db_key = APIKey(
        key=key,
        user_id=user_id,
        tier=tier,
        description=description,
        created_by=created_by,
        expires_at=expires_at,
    )
    db.add(db_key)
    db.commit()
    db.refresh(db_key)
    return db_key


def get_api_key(db: Session, key: str) -> Optional[APIKey]:
    """Get API key by key string."""
    return db.query(APIKey).filter(APIKey.key == key, APIKey.is_active == True).first()


def get_api_key_by_id(db: Session, key_id: int) -> Optional[APIKey]:
    """Get API key by ID."""
    return db.query(APIKey).filter(APIKey.id == key_id).first()


def list_api_keys(db: Session, skip: int = 0, limit: int = 100) -> List[APIKey]:
    """List all API keys."""
    return db.query(APIKey).order_by(desc(APIKey.created_at)).offset(skip).limit(limit).all()


def update_api_key(
    db: Session,
    key_id: int,
    tier: Optional[str] = None,
    is_active: Optional[bool] = None,
    description: Optional[str] = None,
) -> Optional[APIKey]:
    """Update API key."""
    db_key = get_api_key_by_id(db, key_id)
    if not db_key:
        return None

    if tier is not None:
        db_key.tier = tier
    if is_active is not None:
        db_key.is_active = is_active
    if description is not None:
        db_key.description = description

    db_key.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_key)
    return db_key


def delete_api_key(db: Session, key_id: int) -> bool:
    """Delete (soft delete) API key."""
    db_key = get_api_key_by_id(db, key_id)
    if not db_key:
        return False

    db_key.is_active = False
    db_key.updated_at = datetime.utcnow()
    db.commit()
    return True


# Request Log CRUD
def create_request_log(
    db: Session,
    user_id: str,
    api_key_id: Optional[int],
    endpoint: str,
    method: str,
    status_code: int,
    duration_ms: float,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    model: Optional[str] = None,
    error: Optional[str] = None,
) -> RequestLog:
    """Create a request log entry."""
    log = RequestLog(
        user_id=user_id,
        api_key_id=api_key_id,
        endpoint=endpoint,
        method=method,
        status_code=status_code,
        duration_ms=duration_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        model=model,
        error=error,
    )
    db.add(log)
    db.commit()
    return log


def get_usage_stats(db: Session, user_id: Optional[str] = None, days: int = 7):
    """Get usage statistics."""
    query = db.query(
        func.date(RequestLog.timestamp).label("date"),
        func.count(RequestLog.id).label("requests"),
        func.sum(RequestLog.total_tokens).label("total_tokens"),
        func.sum(RequestLog.prompt_tokens).label("prompt_tokens"),
        func.sum(RequestLog.completion_tokens).label("completion_tokens"),
    )

    if user_id:
        query = query.filter(RequestLog.user_id == user_id)

    query = query.filter(
        RequestLog.timestamp >= datetime.utcnow() - func.timedelta(days=days)
    )

    return query.group_by(func.date(RequestLog.timestamp)).all()


# Admin User CRUD
def create_admin_user(db: Session, username: str, password: str, email: Optional[str] = None) -> AdminUser:
    """Create admin user."""
    hashed_password = pwd_context.hash(password)
    admin = AdminUser(
        username=username,
        hashed_password=hashed_password,
        email=email,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


def get_admin_user(db: Session, username: str) -> Optional[AdminUser]:
    """Get admin user by username."""
    return db.query(AdminUser).filter(AdminUser.username == username, AdminUser.is_active == True).first()


def verify_admin_password(plain_password: str, hashed_password: str) -> bool:
    """Verify admin password."""
    return pwd_context.verify(plain_password, hashed_password)


def update_admin_last_login(db: Session, admin_id: int):
    """Update admin last login time."""
    admin = db.query(AdminUser).filter(AdminUser.id == admin_id).first()
    if admin:
        admin.last_login = datetime.utcnow()
        db.commit()


# Verification Code CRUD
def create_verification_code(
    db: Session,
    email: str,
    code: str,
    expires_at: datetime,
    ip_address: Optional[str] = None,
) -> VerificationCode:
    """Create a verification code."""
    verification = VerificationCode(
        email=email,
        code=code,
        expires_at=expires_at,
        ip_address=ip_address,
    )
    db.add(verification)
    db.commit()
    db.refresh(verification)
    return verification


def get_valid_verification_code(db: Session, email: str, code: str) -> Optional[VerificationCode]:
    """Get a valid (not expired, not used) verification code."""
    now = datetime.utcnow()
    return (
        db.query(VerificationCode)
        .filter(
            VerificationCode.email == email,
            VerificationCode.code == code,
            VerificationCode.is_used == False,
            VerificationCode.expires_at > now,
        )
        .first()
    )


def mark_verification_code_used(db: Session, verification_id: int):
    """Mark verification code as used."""
    verification = db.query(VerificationCode).filter(VerificationCode.id == verification_id).first()
    if verification:
        verification.is_used = True
        db.commit()


def cleanup_expired_codes(db: Session) -> int:
    """Delete expired verification codes. Returns number of deleted codes."""
    now = datetime.utcnow()
    count = (
        db.query(VerificationCode)
        .filter(VerificationCode.expires_at < now)
        .delete()
    )
    db.commit()
    return count


def get_api_keys_by_user(db: Session, user_id: str) -> List[APIKey]:
    """Get all API keys for a specific user (email)."""
    return (
        db.query(APIKey)
        .filter(APIKey.user_id == user_id)
        .order_by(desc(APIKey.created_at))
        .all()
    )
