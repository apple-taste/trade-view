from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, String, cast
from datetime import datetime, timedelta, date
from jose import jwt
from passlib.context import CryptContext
import os
import secrets
from typing import Optional
from pathlib import Path

from app.database import get_db, User, Trade, ForexTrade, PaymentOrder, BillingPlanPrice
from app.middleware.auth import get_current_admin, user_has_active_subscription
from app.models import (
    AdminLogin,
    AdminTokenResponse,
    AdminStatsResponse,
    PaginatedAdminUserResponse,
    AdminUserListItem,
    AdminUserUpdate,
    AdminBillingPlanPriceUpdate,
    AdminBillingPlanPricesResponse,
    BillingPlanPriceItem,
    PaginatedPaymentOrderResponse,
    PaymentOrderItem,
    PaymentQrConfigResponse,
    PaymentQrUploadResponse,
)

router = APIRouter()
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
ALGORITHM = "HS256"


def create_admin_token(admin_username: str) -> str:
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode = {"isAdmin": True, "adminUsername": admin_username, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def _resolve_payment_qr_urls() -> tuple[str | None, str | None, str | None]:
    wechat_env = (os.getenv("WECHAT_PAY_QR_URL") or "").strip() or None
    alipay_env = (os.getenv("ALIPAY_PAY_QR_URL") or "").strip() or None
    receiver_note = (os.getenv("PAYMENT_RECEIVER_NOTE") or "").strip() or None

    backend_dir = Path(__file__).resolve().parents[2]
    payment_dir = backend_dir / "static" / "payments"
    db_dir = (os.getenv("DB_DIR") or "").strip()
    if db_dir:
        payment_dir = Path(db_dir) / "payments"

    def find_static(channel: str) -> str | None:
        for ext in (".png", ".jpg", ".jpeg", ".webp"):
            fp = payment_dir / f"{channel}_qr{ext}"
            if fp.exists() and fp.is_file():
                return f"/static/payments/{fp.name}"
        return None

    wechat = find_static("wechat") or wechat_env
    alipay = find_static("alipay") or alipay_env
    return wechat, alipay, receiver_note


@router.get("/billing-prices", response_model=AdminBillingPlanPricesResponse, summary="获取会员价格配置")
async def get_billing_prices(
    _: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(BillingPlanPrice).order_by(BillingPlanPrice.plan.asc()))
    rows = result.scalars().all()
    items = [
        BillingPlanPriceItem(
            plan=str(r.plan),
            unit_price_cents=int(r.unit_price_cents or 0),
            currency=str(r.currency or "CNY"),
            updated_at=getattr(r, "updated_at", None),
        )
        for r in rows
    ]
    return AdminBillingPlanPricesResponse(items=items)


@router.put("/billing-prices/{plan}", response_model=BillingPlanPriceItem, summary="设置会员价格")
async def upsert_billing_price(
    plan: str,
    payload: AdminBillingPlanPriceUpdate,
    _: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    plan_key = (plan or "").strip().lower()
    if not plan_key or plan_key == "free":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的 plan")

    unit_price_cents = int(payload.unit_price_cents or 0)
    if unit_price_cents <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unit_price_cents 必须大于 0")
    if unit_price_cents > 100_000_000:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unit_price_cents 过大")

    currency = (payload.currency or "CNY").strip().upper()
    if currency != "CNY":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持 CNY")

    result = await db.execute(select(BillingPlanPrice).where(BillingPlanPrice.plan == plan_key).limit(1))
    row = result.scalar_one_or_none()
    if row is None:
        row = BillingPlanPrice(plan=plan_key, unit_price_cents=unit_price_cents, currency=currency)
        db.add(row)
    else:
        row.unit_price_cents = unit_price_cents
        row.currency = currency

    await db.commit()
    await db.refresh(row)
    return BillingPlanPriceItem(
        plan=str(row.plan),
        unit_price_cents=int(row.unit_price_cents or 0),
        currency=str(row.currency or "CNY"),
        updated_at=getattr(row, "updated_at", None),
    )


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


@router.get("/payment-qrs", response_model=PaymentQrConfigResponse, summary="获取收款码配置")
async def get_payment_qrs(_: dict = Depends(get_current_admin)):
    wechat, alipay, receiver_note = _resolve_payment_qr_urls()
    return PaymentQrConfigResponse(
        wechat_pay_qr_url=wechat,
        alipay_pay_qr_url=alipay,
        receiver_note=receiver_note,
    )


@router.post("/payment-qrs/{channel}", response_model=PaymentQrUploadResponse, summary="上传收款码")
async def upload_payment_qr(
    channel: str,
    file: UploadFile = File(...),
    _: dict = Depends(get_current_admin),
):
    ch = (channel or "").strip().lower()
    if ch not in {"wechat", "alipay"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="channel 必须是 wechat 或 alipay")

    content_type = (file.content_type or "").strip().lower()
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持图片文件")

    raw_name = (file.filename or "").strip().lower()
    ext = Path(raw_name).suffix if raw_name else ""
    if ext not in {".png", ".jpg", ".jpeg", ".webp"}:
        ext = ".png"

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文件为空")
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文件过大（最大 5MB）")

    backend_dir = Path(__file__).resolve().parents[2]
    payment_dir = backend_dir / "static" / "payments"
    db_dir = (os.getenv("DB_DIR") or "").strip()
    if db_dir:
        payment_dir = Path(db_dir) / "payments"
    payment_dir.mkdir(parents=True, exist_ok=True)

    for old in payment_dir.glob(f"{ch}_qr.*"):
        try:
            old.unlink()
        except Exception:
            pass

    filename = f"{ch}_qr{ext}"
    target = payment_dir / filename
    target.write_bytes(content)

    return PaymentQrUploadResponse(channel=ch, url=f"/static/payments/{filename}")

@router.get("/stats", response_model=AdminStatsResponse, summary="管理员面板统计")
async def get_admin_stats(
    _: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.utcnow()
    cutoff = now - timedelta(days=7)
    beijing_today = (now + timedelta(hours=8)).date()
    paid_grace_cutoff = beijing_today - timedelta(days=7)

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
            .where(or_(User.is_paid == True, and_(User.paid_until != None, User.paid_until >= paid_grace_cutoff)))
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
            is_paid=user_has_active_subscription(u),
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
        is_paid=user_has_active_subscription(user),
        paid_until=getattr(user, "paid_until", None),
        plan=getattr(user, "plan", None),
        total_paid=float(getattr(user, "total_paid", 0.0) or 0.0),
    )


@router.get("/payment-orders", response_model=PaginatedPaymentOrderResponse, summary="支付订单列表")
async def list_payment_orders(
    query: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    page = max(1, int(page))
    page_size = min(200, max(1, int(page_size)))

    stmt = select(PaymentOrder)
    count_stmt = select(func.count()).select_from(PaymentOrder)

    filters = []
    if query:
        q = f"%{query.lower()}%"
        filters.append(or_(func.lower(PaymentOrder.order_no).like(q), cast(PaymentOrder.user_id, String).like(q)))
    if status:
        filters.append(PaymentOrder.status == status)

    if filters:
        cond = and_(*filters)
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)

    total = int((await db.execute(count_stmt)).scalar_one() or 0)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = min(page, total_pages)

    result = await db.execute(
        stmt.order_by(PaymentOrder.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    orders = result.scalars().all()

    items = [
        PaymentOrderItem(
            order_no=o.order_no,
            user_id=o.user_id,
            channel=o.channel,
            amount_cents=o.amount_cents,
            currency=o.currency,
            plan=o.plan,
            months=o.months,
            status=o.status,
            note=o.note,
            approved_by_admin=o.approved_by_admin,
            approved_at=o.approved_at,
            created_at=o.created_at,
            updated_at=o.updated_at,
        )
        for o in orders
    ]

    return PaginatedPaymentOrderResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("/payment-orders/{order_no}/approve", response_model=PaymentOrderItem, summary="审核通过并开通付费")
async def approve_payment_order(
    order_no: str,
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PaymentOrder).where(PaymentOrder.order_no == order_no))
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")

    if order.status in {"approved", "canceled"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="订单状态不允许审核")

    user_result = await db.execute(select(User).where(User.id == order.user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    now = datetime.utcnow()
    today = date.today()
    base = getattr(user, "paid_until", None)
    if base is None or base < today:
        base = today
    new_until = base + timedelta(days=30 * int(order.months or 1))

    user.is_paid = True
    user.plan = order.plan
    user.paid_until = new_until
    user.total_paid = float(getattr(user, "total_paid", 0.0) or 0.0) + float(order.amount_cents or 0) / 100.0

    order.status = "approved"
    order.approved_by_admin = str(admin.get("adminUsername") or "")
    order.approved_at = now

    await db.commit()
    await db.refresh(order)

    return PaymentOrderItem(
        order_no=order.order_no,
        user_id=order.user_id,
        channel=order.channel,
        amount_cents=order.amount_cents,
        currency=order.currency,
        plan=order.plan,
        months=order.months,
        status=order.status,
        note=order.note,
        approved_by_admin=order.approved_by_admin,
        approved_at=order.approved_at,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


@router.post("/payment-orders/{order_no}/cancel", response_model=PaymentOrderItem, summary="取消支付订单")
async def cancel_payment_order(
    order_no: str,
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PaymentOrder).where(PaymentOrder.order_no == order_no))
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")

    if order.status == "approved":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="已审核订单不能取消")

    order.status = "canceled"
    order.approved_by_admin = str(admin.get("adminUsername") or "")
    order.approved_at = datetime.utcnow()

    await db.commit()
    await db.refresh(order)

    return PaymentOrderItem(
        order_no=order.order_no,
        user_id=order.user_id,
        channel=order.channel,
        amount_cents=order.amount_cents,
        currency=order.currency,
        plan=order.plan,
        months=order.months,
        status=order.status,
        note=order.note,
        approved_by_admin=order.approved_by_admin,
        approved_at=order.approved_at,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )
