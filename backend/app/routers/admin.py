from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from datetime import datetime, timedelta, date
from jose import jwt
from passlib.context import CryptContext
import os
import secrets
from typing import Optional

from app.database import get_db, User, Trade, ForexTrade
from app.middleware.auth import get_current_admin
from app.models import (
    AdminLogin,
    AdminTokenResponse,
    AdminStatsResponse,
    PaginatedAdminUserResponse,
    AdminUserListItem,
    AdminUserUpdate,
)

router = APIRouter()
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
ALGORITHM = "HS256"


def create_admin_token(admin_username: str) -> str:
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode = {"isAdmin": True, "adminUsername": admin_username, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


@router.post("/login", response_model=AdminTokenResponse, summary="管理员登录")
async def admin_login(payload: AdminLogin):
    admin_username = os.getenv("ADMIN_USERNAME")
    admin_password = os.getenv("ADMIN_PASSWORD")
    admin_password_hash = os.getenv("ADMIN_PASSWORD_HASH")

    if not admin_username or (not admin_password and not admin_password_hash):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="管理员未配置")

    if not secrets.compare_digest(str(payload.username), str(admin_username)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")

    if admin_password_hash:
        ok = pwd_context.verify(payload.password, admin_password_hash)
    else:
        ok = secrets.compare_digest(str(payload.password), str(admin_password or ""))

    if not ok:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")

    token = create_admin_token(admin_username)
    return AdminTokenResponse(token=token, admin_username=admin_username)


@router.get("/stats", response_model=AdminStatsResponse, summary="管理员面板统计")
async def get_admin_stats(
    _: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.utcnow()
    cutoff = now - timedelta(days=7)
    today = date.today()

    total_users = (
        await db.execute(select(func.count()).select_from(User))
    ).scalar_one()

    new_users_7d = (
        await db.execute(select(func.count()).select_from(User).where(User.created_at >= cutoff))
    ).scalar_one()

    paid_users = (
        await db.execute(
            select(func.count())
            .select_from(User)
            .where(or_(User.is_paid == True, and_(User.paid_until != None, User.paid_until >= today)))
        )
    ).scalar_one()

    total_revenue = (
        await db.execute(select(func.coalesce(func.sum(User.total_paid), 0.0)).select_from(User))
    ).scalar_one()

    active_ids = (
        select(User.id.label("user_id")).where(User.last_login_at != None, User.last_login_at >= cutoff)
    ).union(
        select(Trade.user_id.label("user_id")).where(Trade.is_deleted == False, Trade.open_time >= cutoff),
        select(ForexTrade.user_id.label("user_id")).where(ForexTrade.is_deleted == False, ForexTrade.open_time >= cutoff),
    )

    active_ids_subq = active_ids.subquery()
    active_users_7d = (
        await db.execute(select(func.count(func.distinct(active_ids_subq.c.user_id))))
    ).scalar_one()

    return AdminStatsResponse(
        total_users=int(total_users or 0),
        new_users_7d=int(new_users_7d or 0),
        active_users_7d=int(active_users_7d or 0),
        paid_users=int(paid_users or 0),
        total_revenue=float(total_revenue or 0.0),
    )


@router.get("/users", response_model=PaginatedAdminUserResponse, summary="用户列表")
async def list_users(
    query: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    _: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    page = max(1, int(page))
    page_size = min(200, max(1, int(page_size)))

    stmt = select(User)
    count_stmt = select(func.count()).select_from(User)

    if query:
        q = f"%{query.lower()}%"
        filter_expr = or_(func.lower(User.username).like(q), func.lower(User.email).like(q))
        stmt = stmt.where(filter_expr)
        count_stmt = count_stmt.where(filter_expr)

    total = (await db.execute(count_stmt)).scalar_one()
    total_pages = max(1, (int(total or 0) + page_size - 1) // page_size)
    page = min(page, total_pages)

    result = await db.execute(
        stmt.order_by(User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    users = result.scalars().all()

    items = [
        AdminUserListItem(
            id=u.id,
            username=u.username,
            email=u.email,
            created_at=u.created_at,
            last_login_at=getattr(u, "last_login_at", None),
            is_paid=bool(getattr(u, "is_paid", False)),
            paid_until=getattr(u, "paid_until", None),
            plan=getattr(u, "plan", None),
            total_paid=float(getattr(u, "total_paid", 0.0) or 0.0),
        )
        for u in users
    ]

    return PaginatedAdminUserResponse(
        items=items,
        total=int(total or 0),
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.patch("/users/{user_id}", response_model=AdminUserListItem, summary="更新用户付费信息")
async def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    _: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    if payload.is_paid is not None:
        user.is_paid = bool(payload.is_paid)
    fields_set = getattr(payload, "model_fields_set", getattr(payload, "__fields_set__", set()))
    if "paid_until" in fields_set:
        user.paid_until = payload.paid_until
    if payload.plan is not None:
        user.plan = payload.plan
    if payload.total_paid is not None:
        if payload.total_paid < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="total_paid 不能为负数")
        user.total_paid = float(payload.total_paid)

    await db.commit()
    await db.refresh(user)

    return AdminUserListItem(
        id=user.id,
        username=user.username,
        email=user.email,
        created_at=user.created_at,
        last_login_at=getattr(user, "last_login_at", None),
        is_paid=bool(getattr(user, "is_paid", False)),
        paid_until=getattr(user, "paid_until", None),
        plan=getattr(user, "plan", None),
        total_paid=float(getattr(user, "total_paid", 0.0) or 0.0),
    )
