from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
import asyncio

from app.database import get_db, User
import os
from datetime import date, datetime, timedelta


def billing_enabled() -> bool:
    v = (os.getenv("BILLING_ENABLED", "false") or "").strip().lower()
    return v in {"1", "true", "yes", "on"}


def user_has_active_subscription(user: User) -> bool:
    if bool(getattr(user, "is_paid", False)):
        return True
    paid_until = getattr(user, "paid_until", None)
    if paid_until is None:
        return False
    beijing_today = (datetime.utcnow() + timedelta(hours=8)).date()
    grace_period = timedelta(days=7)
    return bool(paid_until + grace_period >= beijing_today)

SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
ALGORITHM = "HS256"

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("userId")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    db_timeout_s = float(os.getenv("DB_QUERY_TIMEOUT", "8"))
    try:
        result = await asyncio.wait_for(db.execute(select(User).where(User.id == user_id)), timeout=db_timeout_s)
    except (asyncio.TimeoutError, TimeoutError, SQLAlchemyError):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库暂不可用，请稍后重试")
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    
    return user

async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        is_admin = bool(payload.get("isAdmin"))
        if is_admin:
            return payload

        user_id = payload.get("userId")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    db_timeout_s = float(os.getenv("DB_QUERY_TIMEOUT", "8"))
    try:
        result = await asyncio.wait_for(db.execute(select(User).where(User.id == user_id)), timeout=db_timeout_s)
    except (asyncio.TimeoutError, TimeoutError, SQLAlchemyError):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库暂不可用，请稍后重试")
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception

    if not bool(getattr(user, "is_admin", False)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")

    return {"userId": user.id, "isAdmin": True}
