from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from datetime import date, datetime, timedelta
import uuid

from app.database import (
    get_db,
    User,
    CapitalHistory,
    Trade,
    Strategy,
    StrategyCapitalHistory,
    ForexTrade,
    ForexAccount,
    PaymentOrder,
    BillingPlanPrice,
)
from app.middleware.auth import get_current_user, billing_enabled, user_has_active_subscription
from app.models import (
    CapitalUpdate,
    CapitalHistoryItem,
    UserResponse,
    StrategyCreate,
    StrategyResponse,
    BillingStatusResponse,
    BillingPricingResponse,
    PaymentOrderCreate,
    PaymentOrderNoteUpdate,
    PaymentOrderItem,
    PaymentOrderCreateResponse,
    PaymentQrConfigResponse,
)
from app.services.commission_calculator import default_calculator
from app.services.email_service import default_email_service
import os
from pathlib import Path

router = APIRouter()


async def _resolve_plan_unit_price_cents(db: AsyncSession, plan: str) -> tuple[int, str]:
    plan_key = (plan or "").strip().lower()
    if plan_key == "free":
        return 0, "CNY"

    result = await db.execute(select(BillingPlanPrice).where(BillingPlanPrice.plan == plan_key).limit(1))
    row = result.scalar_one_or_none()
    if row and int(getattr(row, "unit_price_cents", 0) or 0) > 0:
        return int(row.unit_price_cents), str(row.currency or "CNY")

    env_key = f"BILLING_PLAN_{plan_key.upper()}_PRICE_CENTS"
    raw = (os.getenv(env_key, "") or "").strip()
    if raw.isdigit():
        unit_price = int(raw)
    else:
        unit_price = 9900 if plan_key == "pro" else 19900

    return int(unit_price), "CNY"


async def _get_price_cents(db: AsyncSession, plan: str, months: int) -> tuple[int, int, str]:
    plan_key = (plan or "").strip().lower()
    if plan_key == "free":
        return 0, 0, "CNY"
    if months <= 0:
        raise HTTPException(status_code=400, detail="months 必须大于 0")

    unit_price_cents, currency = await _resolve_plan_unit_price_cents(db, plan_key)
    amount_cents = int(unit_price_cents) * int(months)
    return int(unit_price_cents), int(amount_cents), str(currency or "CNY")


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

async def _ensure_default_stock_strategy(db: AsyncSession, user: User) -> Strategy:
    result = await db.execute(
        select(Strategy)
        .where(Strategy.user_id == user.id, Strategy.market == "stock")
        .order_by(Strategy.id.asc())
        .limit(1)
    )
    existing = result.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="请先创建策略")
    await _migrate_legacy_stock_data_to_strategy(db, user, existing)
    return existing

async def _migrate_legacy_stock_data_to_strategy(db: AsyncSession, user: User, strategy: Strategy) -> None:
    count_result = await db.execute(
        select(func.count(StrategyCapitalHistory.id)).where(
            StrategyCapitalHistory.user_id == user.id,
            StrategyCapitalHistory.strategy_id == strategy.id,
        )
    )
    existing_count = int(count_result.scalar() or 0)
    if existing_count <= 1:
        legacy_result = await db.execute(
            select(CapitalHistory)
            .where(CapitalHistory.user_id == user.id)
            .order_by(CapitalHistory.date.asc())
        )
        legacy = legacy_result.scalars().all()
        if legacy:
            existing_dates_result = await db.execute(
                select(StrategyCapitalHistory.date).where(
                    StrategyCapitalHistory.user_id == user.id,
                    StrategyCapitalHistory.strategy_id == strategy.id,
                )
            )
            existing_dates = {row[0] for row in existing_dates_result.fetchall()}
            for h in legacy:
                if h.date in existing_dates:
                    continue
                db.add(
                    StrategyCapitalHistory(
                        user_id=user.id,
                        strategy_id=strategy.id,
                        date=h.date,
                        capital=h.capital,
                        available_funds=h.available_funds,
                        position_value=h.position_value if h.position_value is not None else 0.0,
                    )
                )

    trades_result = await db.execute(
        select(Trade).where(
            Trade.user_id == user.id,
            Trade.strategy_id.is_(None),
        )
    )
    trades = trades_result.scalars().all()
    for t in trades:
        t.strategy_id = strategy.id
    await db.commit()

async def _migrate_legacy_forex_data_to_strategy(db: AsyncSession, user: User, strategy: Strategy) -> None:
    result = await db.execute(
        select(ForexTrade).where(
            ForexTrade.user_id == user.id,
            ForexTrade.strategy_id.is_(None),
        )
    )
    trades = result.scalars().all()
    for t in trades:
        t.strategy_id = strategy.id
    await db.commit()

async def _get_stock_strategy(db: AsyncSession, user: User, strategy_id: int | None) -> Strategy:
    if strategy_id is None:
        raise HTTPException(status_code=400, detail="请先选择策略")

    result = await db.execute(
        select(Strategy).where(
            Strategy.id == strategy_id,
            Strategy.user_id == user.id,
            Strategy.market == "stock",
        )
    )
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")
    return strategy

async def _get_forex_strategy(db: AsyncSession, user: User, strategy_id: int | None) -> Strategy:
    if strategy_id is None:
        raise HTTPException(status_code=400, detail="请先选择策略")

    result = await db.execute(
        select(Strategy).where(
            Strategy.id == strategy_id,
            Strategy.user_id == user.id,
            Strategy.market == "forex",
        )
    )
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")
    return strategy

@router.get(
    "/profile",
    response_model=UserResponse,
    summary="获取用户信息",
    description="获取当前登录用户的详细信息，包括用户ID、用户名、邮箱和注册时间。",
    responses={
        200: {"description": "成功返回用户信息"},
        401: {"description": "未认证或Token无效"}
    }
)
async def get_profile(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        email_alerts_enabled=current_user.email_alerts_enabled or False,
        created_at=current_user.created_at
    )


@router.get("/billing-status", response_model=BillingStatusResponse, summary="获取计费状态")
async def get_billing_status(current_user: User = Depends(get_current_user)):
    return BillingStatusResponse(
        billing_enabled=billing_enabled(),
        is_paid=user_has_active_subscription(current_user),
        paid_until=getattr(current_user, "paid_until", None),
        plan=getattr(current_user, "plan", None),
    )


@router.get("/payment-qrs", response_model=PaymentQrConfigResponse, summary="获取收款码配置")
async def get_payment_qrs(_: User = Depends(get_current_user)):
    wechat, alipay, receiver_note = _resolve_payment_qr_urls()
    return PaymentQrConfigResponse(
        wechat_pay_qr_url=wechat,
        alipay_pay_qr_url=alipay,
        receiver_note=receiver_note,
    )


@router.get("/billing-plans/{plan}/price", response_model=BillingPricingResponse, summary="获取会员价格")
async def get_billing_plan_price(
    plan: str,
    months: int = 1,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    plan_key = (plan or "").strip().lower()
    unit_price_cents, amount_cents, currency = await _get_price_cents(db, plan_key, int(months or 1))
    return BillingPricingResponse(
        plan=plan_key,
        months=int(months or 1),
        unit_price_cents=unit_price_cents,
        amount_cents=amount_cents,
        currency=currency,
    )


@router.post("/payment-orders", response_model=PaymentOrderCreateResponse, summary="创建支付订单（微信/支付宝）")
async def create_payment_order(
    payload: PaymentOrderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not billing_enabled():
        raise HTTPException(status_code=400, detail="当前未开启收费")

    channel = (payload.channel or "").strip().lower()
    if channel not in {"wechat", "alipay"}:
        raise HTTPException(status_code=400, detail="channel 必须是 wechat 或 alipay")

    plan = (payload.plan or "pro").strip().lower()
    months = int(payload.months or 1)
    _, amount_cents, currency = await _get_price_cents(db, plan, months)
    if amount_cents <= 0:
        raise HTTPException(status_code=400, detail="该套餐不可购买")

    order_no = uuid.uuid4().hex
    order = PaymentOrder(
        user_id=current_user.id,
        order_no=order_no,
        channel=channel,
        amount_cents=amount_cents,
        currency=currency,
        plan=plan,
        months=months,
        status="pending",
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)

    wechat_pay_qr_url, alipay_pay_qr_url, receiver_note = _resolve_payment_qr_urls()

    parts = [
        f"订单号：{order_no}",
        f"金额：{amount_cents / 100:.2f} CNY",
        f"渠道：{'微信' if channel == 'wechat' else '支付宝'}",
        "请完成支付后，等待管理员审核开通。",
    ]
    if receiver_note:
        parts.append(receiver_note)
    instructions = "\n".join(parts)

    return PaymentOrderCreateResponse(
        order=PaymentOrderItem(
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
        ),
        instructions=instructions,
        wechat_pay_qr_url=wechat_pay_qr_url,
        alipay_pay_qr_url=alipay_pay_qr_url,
    )


@router.get("/payment-orders", response_model=list[PaymentOrderItem], summary="查看我的支付订单")
async def list_my_payment_orders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PaymentOrder)
        .where(PaymentOrder.user_id == current_user.id)
        .order_by(PaymentOrder.created_at.desc())
        .limit(50)
    )
    orders = result.scalars().all()
    return [
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


@router.get("/payment-orders/{order_no}", response_model=PaymentOrderItem, summary="查看我的支付订单详情")
async def get_my_payment_order(
    order_no: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PaymentOrder).where(PaymentOrder.order_no == order_no, PaymentOrder.user_id == current_user.id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="订单不存在")

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


@router.patch("/payment-orders/{order_no}/note", response_model=PaymentOrderItem, summary="更新支付订单备注")
async def update_my_payment_order_note(
    order_no: str,
    payload: PaymentOrderNoteUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    note = (payload.note or "").strip()
    if not note:
        raise HTTPException(status_code=400, detail="note 不能为空")
    if len(note) > 500:
        raise HTTPException(status_code=400, detail="note 过长（最多 500 字）")

    result = await db.execute(
        select(PaymentOrder).where(PaymentOrder.order_no == order_no, PaymentOrder.user_id == current_user.id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status != "pending":
        raise HTTPException(status_code=400, detail="仅可修改待审核订单的备注")

    order.note = note
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

@router.post(
    "/email-alerts",
    response_model=UserResponse,
    summary="更新邮箱提醒设置",
    description="启用或禁用价格提醒的邮箱通知功能。",
    responses={
        200: {"description": "成功更新邮箱提醒设置"},
        401: {"description": "未认证或Token无效"}
    }
)
async def update_email_alerts(
    enabled: bool,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    current_user.email_alerts_enabled = enabled
    await db.commit()
    await db.refresh(current_user)
    
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        email_alerts_enabled=current_user.email_alerts_enabled,
        created_at=current_user.created_at
    )

@router.post(
    "/test-email",
    summary="发送测试邮件",
    description="测试邮件通知功能是否正常工作",
    responses={
        200: {"description": "测试邮件发送成功"},
        400: {"description": "邮件服务未配置"},
        500: {"description": "发送失败"}
    }
)
async def send_test_email(
    current_user: User = Depends(get_current_user)
):
    # 检查邮件服务是否配置
    if not default_email_service.is_configured():
        raise HTTPException(
            status_code=400,
            detail="邮件服务未配置。请在后端.env文件中配置SMTP服务器信息。"
        )
    
    # 发送测试邮件
    success = default_email_service.send_price_alert(
        to_email=current_user.email,
        stock_code="TEST",
        stock_name="测试股票",
        alert_type="take_profit",
        current_price=99.99,
        target_price=100.00
    )
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="邮件发送失败。请检查SMTP配置和网络连接。"
        )
    
    return {"message": "测试邮件已发送", "email": current_user.email}

@router.get(
    "/capital-history",
    response_model=list[CapitalHistoryItem],
    summary="获取资金历史",
    description="""
    获取用户的资金历史记录，用于绘制资金曲线。
    
    - **start_date**: 可选，开始日期，格式：YYYY-MM-DD
    - **end_date**: 可选，结束日期，格式：YYYY-MM-DD
    
    如果不提供日期参数，返回所有历史记录。
    """,
    responses={
        200: {"description": "成功返回资金历史列表"}
    }
)
async def get_capital_history(
    start_date: date | None = None,
    end_date: date | None = None,
    strategy_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户的资金历史记录，用于绘制资金曲线。
    
    重要：当用户更新资金后，会删除该日期之后的所有记录并重新计算。
    因此，返回的数据应该从最早的记录开始（即用户设置的初始资金日期）。
    """
    if strategy_id is None:
        query = select(CapitalHistory).where(CapitalHistory.user_id == current_user.id)
    else:
        strategy = await _get_stock_strategy(db, current_user, strategy_id)
        await _ensure_strategy_capital_history_uptodate(db, current_user.id, strategy.id)
        query = select(StrategyCapitalHistory).where(
            StrategyCapitalHistory.user_id == current_user.id,
            StrategyCapitalHistory.strategy_id == strategy.id,
        )
    
    if start_date:
        query = query.where((StrategyCapitalHistory.date if strategy_id is not None else CapitalHistory.date) >= start_date)
    if end_date:
        query = query.where((StrategyCapitalHistory.date if strategy_id is not None else CapitalHistory.date) <= end_date)
    
    query = query.order_by((StrategyCapitalHistory.date if strategy_id is not None else CapitalHistory.date).asc())
    
    result = await db.execute(query)
    history = result.scalars().all()
    
    # 如果用户提供了start_date，直接返回
    # 如果没有提供start_date，返回所有记录（这些记录都是从用户设置的初始资金日期开始的）
    return [
        CapitalHistoryItem(
            date=h.date,
            capital=h.capital,
            available_funds=h.available_funds,
            position_value=h.position_value if h.position_value is not None else 0.0
        )
        for h in history
    ]


@router.post("/capital-history/recalculate", summary="手动重算资金曲线")
async def recalculate_capital_history_endpoint(
    strategy_id: int | None = None,
    start_date: date | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if strategy_id is None:
        anchor = start_date or getattr(current_user, "initial_capital_date", None) or date.today()
        await recalculate_capital_history(db, current_user.id, anchor)
        return {"message": "资金曲线已重算", "strategy_id": None, "start_date": str(anchor)}

    strategy = await _get_stock_strategy(db, current_user, strategy_id)
    anchor = start_date or getattr(strategy, "initial_date", None) or getattr(current_user, "initial_capital_date", None) or date.today()
    await recalculate_strategy_capital_history(db, current_user.id, strategy.id, anchor)
    return {"message": "资金曲线已重算", "strategy_id": strategy.id, "start_date": str(anchor)}

@router.post(
    "/capital",
    summary="设置初始资金（策略回测起点）",
    description="""
    设置用户的初始资金，这是**策略回测**的起点。
    
    - **capital**: 初始资金金额（必填）
    - **date**: 回测起始日期，格式：YYYY-MM-DD（可选，默认为今天）
    
    **策略回测功能**:
    - 设置初始资金后，系统会从该日期开始，按照时间顺序重新计算所有交易
    - 生成完整的资金曲线，用于回测分析
    - 回测逻辑：
      1. 从设置的日期开始，使用设置的初始资金
      2. 按时间顺序处理所有交易（开仓和平仓）
      3. 开仓时：资金减少 = 买入价×手数 + 手续费
      4. 平仓时：资金增加 = 卖出价×手数 - 手续费（包含本金回收和盈亏）
      5. 记录每个有交易日期的资金变化，形成连续的资金曲线
    
    **重要说明**:
    - 设置初始资金会清除该日期之后的所有资金历史记录
    - 然后根据交易记录从该日期开始重新计算资金曲线
    - 这允许您进行策略回测：假设从某个日期开始，用某个初始资金，按照历史交易记录，最终资金会是多少
    """,
    responses={
        200: {"description": "初始资金设置成功"}
    }
)
async def update_capital(
    capital_data: CapitalUpdate,
    strategy_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 处理日期：如果 capital_data.date 是字符串，转换为 date 对象
    if capital_data.date is None:
        update_date = date.today()
    elif isinstance(capital_data.date, str):
        try:
            update_date = datetime.strptime(capital_data.date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD 格式")
    else:
        update_date = capital_data.date
    
    if strategy_id is None:
        result = await db.execute(
            select(CapitalHistory).where(
                CapitalHistory.user_id == current_user.id,
                CapitalHistory.date >= update_date
            )
        )
        old_records = result.scalars().all()
        for record in old_records:
            await db.delete(record)
        
        result = await db.execute(
            select(CapitalHistory).where(
                CapitalHistory.user_id == current_user.id,
                CapitalHistory.date < update_date
            )
        )
        old_before_records = result.scalars().all()
        for record in old_before_records:
            await db.delete(record)
        
        current_user.initial_capital = capital_data.capital
        current_user.initial_capital_date = update_date

        result = await db.execute(
            select(CapitalHistory).where(
                CapitalHistory.user_id == current_user.id,
                CapitalHistory.date == update_date
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            existing.capital = capital_data.capital
            existing.available_funds = capital_data.capital
            existing.position_value = 0.0
        else:
            db.add(
                CapitalHistory(
                    user_id=current_user.id,
                    date=update_date,
                    capital=capital_data.capital,
                    available_funds=capital_data.capital,
                    position_value=0.0
                )
            )
        
        await db.commit()
        await recalculate_capital_history(db, current_user.id, update_date)
        return {"message": "初始资金设置成功，资金曲线已重新计算"}

    strategy = await _get_stock_strategy(db, current_user, strategy_id)
    strategy.initial_capital = float(capital_data.capital)
    strategy.initial_date = update_date

    result = await db.execute(
        select(StrategyCapitalHistory).where(
            StrategyCapitalHistory.user_id == current_user.id,
            StrategyCapitalHistory.strategy_id == strategy.id,
            StrategyCapitalHistory.date >= update_date,
        )
    )
    old_records = result.scalars().all()
    for record in old_records:
        await db.delete(record)

    result = await db.execute(
        select(StrategyCapitalHistory).where(
            StrategyCapitalHistory.user_id == current_user.id,
            StrategyCapitalHistory.strategy_id == strategy.id,
            StrategyCapitalHistory.date < update_date,
        )
    )
    old_before_records = result.scalars().all()
    for record in old_before_records:
        await db.delete(record)

    db.add(
        StrategyCapitalHistory(
            user_id=current_user.id,
            strategy_id=strategy.id,
            date=update_date,
            capital=float(capital_data.capital),
            available_funds=float(capital_data.capital),
            position_value=0.0,
        )
    )
    await db.commit()
    await recalculate_strategy_capital_history(db, current_user.id, strategy.id, update_date)
    return {"message": "初始资金设置成功，资金曲线已重新计算"}

async def get_current_total_assets(db: AsyncSession, user_id: int, strategy_id: int | None = None):
    """
    计算当前实时总资产（同花顺模式）
    
    总资产 = 可用资金 + 实时持仓市值
    
    注意：这里使用的是持仓股票的最新市场价格（current_price），
    而历史资金曲线使用的是买入价（持仓成本）。
    """
    if strategy_id is None:
        result = await db.execute(
            select(CapitalHistory)
            .where(CapitalHistory.user_id == user_id)
            .order_by(CapitalHistory.date.desc())
            .limit(1)
        )
        latest_record = result.scalar_one_or_none()
    else:
        await _ensure_strategy_capital_history_uptodate(db, user_id, int(strategy_id))
        result = await db.execute(
            select(StrategyCapitalHistory)
            .where(
                StrategyCapitalHistory.user_id == user_id,
                StrategyCapitalHistory.strategy_id == strategy_id,
            )
            .order_by(StrategyCapitalHistory.date.desc())
            .limit(1)
        )
        latest_record = result.scalar_one_or_none()
    
    if latest_record and latest_record.available_funds is not None:
        available_funds = latest_record.available_funds
    elif latest_record:
        available_funds = latest_record.capital
    else:
        available_funds = 100000.0
    
    if strategy_id is None:
        result = await db.execute(
            select(Trade)
            .where(
                Trade.user_id == user_id,
                Trade.status == "open",
                Trade.close_time.is_(None),
                Trade.sell_price.is_(None),
                Trade.is_deleted == False
            )
        )
    else:
        result = await db.execute(
            select(Trade)
            .where(
                Trade.user_id == user_id,
                Trade.strategy_id == strategy_id,
                Trade.status == "open",
                Trade.close_time.is_(None),
                Trade.sell_price.is_(None),
                Trade.is_deleted == False
            )
        )
    open_positions = result.scalars().all()
    
    # 计算实时持仓市值（使用最新市场价格）
    position_value = 0.0
    for pos in open_positions:
        # 使用最新价格（如果有），否则使用买入价
        price = pos.current_price if pos.current_price else pos.buy_price
        position_value += price * pos.shares
    
    # 计算实时总资产
    total_assets = available_funds + position_value
    
    return {
        "total_assets": total_assets,
        "available_funds": available_funds,
        "position_value": position_value
    }

@router.get(
    "/capital",
    summary="获取当前资金（同花顺模式）",
    description="""
    获取用户最新的资金信息（同花顺模式）。
    
    返回数据：
    - **total_assets**: 实时总资产 = 可用资金 + 实时持仓市值（使用最新市场价格）
    - **available_funds**: 可用资金（可用于开新仓）
    - **position_value**: 实时持仓市值（所有持仓股票的最新市场价格）
    - **capital**: 总资产（兼容旧接口）
    
    注意：
    - 实时总资产使用持仓股票的最新市场价格（current_price）
    - 历史资金曲线使用买入价（持仓成本）作为保守估计
    
    如果没有历史记录，返回默认值10万元。
    """,
    responses={
        200: {
            "description": "成功返回当前资金",
            "content": {
                "application/json": {
                    "example": {
                        "capital": 105000.0,
                        "total_assets": 105000.0,
                        "available_funds": 50000.0,
                        "position_value": 55000.0
                    }
                }
            }
        }
    }
)
async def get_current_capital(
    strategy_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if strategy_id is not None:
        strategy = await _get_stock_strategy(db, current_user, strategy_id)
        assets_info = await get_current_total_assets(db, current_user.id, strategy.id)
    else:
        assets_info = await get_current_total_assets(db, current_user.id)
    
    return {
        "capital": assets_info["total_assets"],  # 总资产（兼容旧接口）
        "total_assets": assets_info["total_assets"],
        "available_funds": assets_info["available_funds"],
        "position_value": assets_info["position_value"]
    }

async def recalculate_strategy_capital_history(db: AsyncSession, user_id: int, strategy_id: int, start_date: date):
    strategy_result = await db.execute(
        select(Strategy).where(Strategy.id == strategy_id, Strategy.user_id == user_id, Strategy.market == "stock")
    )
    strategy = strategy_result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")

    if strategy.initial_date is None:
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()

        min_dt_result = await db.execute(
            select(func.min(Trade.open_time), func.min(Trade.close_time)).where(
                Trade.user_id == user_id,
                Trade.strategy_id == strategy_id,
                Trade.is_deleted == False,
            )
        )
        min_open_dt, min_close_dt = min_dt_result.one()
        earliest_trade_dt = None
        for dt in (min_open_dt, min_close_dt):
            if dt is None:
                continue
            if earliest_trade_dt is None or dt < earliest_trade_dt:
                earliest_trade_dt = dt

        candidates: list[date] = []
        if user and user.initial_capital_date:
            candidates.append(user.initial_capital_date)
        if earliest_trade_dt is not None:
            candidates.append(earliest_trade_dt.date())

        strategy.initial_date = min(candidates) if candidates else date.today()
        if strategy.initial_capital is None:
            strategy.initial_capital = float(user.initial_capital) if user and user.initial_capital is not None else 100000.0

    anchor_date = strategy.initial_date
    initial_capital = float(strategy.initial_capital) if strategy.initial_capital is not None else 100000.0
    start_date = anchor_date

    result = await db.execute(
        select(StrategyCapitalHistory).where(
            StrategyCapitalHistory.user_id == user_id,
            StrategyCapitalHistory.strategy_id == strategy_id,
            StrategyCapitalHistory.date == anchor_date
        )
    )
    initial_record = result.scalar_one_or_none()
    if not initial_record:
        initial_record = StrategyCapitalHistory(
            user_id=user_id,
            strategy_id=strategy_id,
            date=anchor_date,
            capital=initial_capital,
            available_funds=initial_capital,
            position_value=0.0,
        )
        db.add(initial_record)
        await db.flush()

    available_funds = initial_capital
    position_value = 0.0
    positions: dict[int, Trade] = {}
    if start_date > anchor_date:
        prev_result = await db.execute(
            select(StrategyCapitalHistory)
            .where(
                StrategyCapitalHistory.user_id == user_id,
                StrategyCapitalHistory.strategy_id == strategy_id,
                StrategyCapitalHistory.date < start_date,
            )
            .order_by(StrategyCapitalHistory.date.desc())
            .limit(1)
        )
        prev_record = prev_result.scalar_one_or_none() or initial_record
        prev_date = prev_record.date
        available_funds = float(prev_record.available_funds) if prev_record.available_funds is not None else float(prev_record.capital)

        open_pos_result = await db.execute(
            select(Trade).where(
                Trade.user_id == user_id,
                Trade.strategy_id == strategy_id,
                Trade.is_deleted == False,
                Trade.open_time.isnot(None),
                func.date(Trade.open_time) <= prev_date,
                or_(
                    and_(
                        Trade.close_time.isnot(None),
                        func.date(Trade.close_time) > prev_date,
                    ),
                    Trade.close_time.is_(None),
                ),
            )
        )
        open_positions = open_pos_result.scalars().all()
        positions = {t.id: t for t in open_positions}
        position_value = sum((t.buy_price or 0) * (t.shares or 0) for t in open_positions)

    result = await db.execute(
        select(Trade)
        .where(
            Trade.user_id == user_id,
            Trade.strategy_id == strategy_id,
            Trade.is_deleted == False,
            or_(
                func.date(Trade.open_time) >= start_date,
                and_(
                    Trade.close_time.isnot(None),
                    func.date(Trade.close_time) >= start_date
                )
            )
        )
        .order_by(Trade.open_time.asc())
    )
    trades = result.scalars().all()

    trade_events = []
    for trade in trades:
        open_date = trade.open_time.date()
        if open_date >= start_date:
            trade_events.append({'date': open_date, 'time': trade.open_time, 'type': 'open', 'trade': trade})
        if trade.sell_price is not None:
            close_dt = trade.close_time or trade.updated_at or trade.open_time
            if close_dt is not None and trade.open_time is not None and close_dt < trade.open_time:
                close_dt = trade.open_time
            if close_dt is not None:
                close_date = close_dt.date()
                if close_date >= start_date:
                    trade_events.append({'date': close_date, 'time': close_dt, 'type': 'close', 'trade': trade})
    trade_events.sort(key=lambda x: (x['date'], x['time']))

    capital_records: dict[date, tuple[float, float, float]] = {}
    if start_date == anchor_date:
        capital_records[start_date] = (initial_capital, 0.0, initial_capital)

    if not trade_events:
        if start_date == anchor_date:
            result = await db.execute(
                select(StrategyCapitalHistory).where(
                    StrategyCapitalHistory.user_id == user_id,
                    StrategyCapitalHistory.strategy_id == strategy_id,
                    StrategyCapitalHistory.date != anchor_date
                )
            )
            records_to_delete = result.scalars().all()
            for record in records_to_delete:
                await db.delete(record)

            initial_record.capital = initial_capital
            initial_record.available_funds = initial_capital
            initial_record.position_value = 0.0
            await db.commit()
            return

        result = await db.execute(
            select(StrategyCapitalHistory).where(
                StrategyCapitalHistory.user_id == user_id,
                StrategyCapitalHistory.strategy_id == strategy_id,
                StrategyCapitalHistory.date >= start_date,
            )
        )
        records_to_delete = result.scalars().all()
        for record in records_to_delete:
            await db.delete(record)
        await db.commit()
        return

    for event in trade_events:
        trade_date = event['date']
        trade = event['trade']

        if event['type'] == 'open':
            buy_commission = trade.buy_commission if trade.buy_commission is not None else (trade.commission or 0)
            cost = trade.buy_price * trade.shares + buy_commission
            available_funds -= cost
            positions[trade.id] = trade
        elif event['type'] == 'close' and trade.sell_price is not None:
            if trade.profit_loss is not None:
                buy_commission = trade.buy_commission if trade.buy_commission is not None else (trade.commission or 0)
                buy_cost = trade.buy_price * trade.shares + buy_commission
                available_funds += buy_cost + trade.profit_loss
            else:
                sell_amount = trade.sell_price * trade.shares
                if trade.sell_commission is not None:
                    sell_commission = trade.sell_commission
                else:
                    sell_commission = default_calculator.calculate_sell_commission(
                        trade.sell_price,
                        trade.shares,
                        trade.stock_code
                    )
                available_funds += sell_amount - sell_commission
            positions.pop(trade.id, None)
        position_value = sum((t.buy_price or 0) * (t.shares or 0) for t in positions.values())
        total_assets = available_funds + position_value
        capital_records[trade_date] = (available_funds, position_value, total_assets)

    existing_result = await db.execute(
        select(StrategyCapitalHistory).where(
            StrategyCapitalHistory.user_id == user_id,
            StrategyCapitalHistory.strategy_id == strategy_id,
            StrategyCapitalHistory.date >= start_date,
        )
    )
    existing_records = existing_result.scalars().all()
    existing_by_date: dict[date, StrategyCapitalHistory] = {r.date: r for r in existing_records}

    keep_dates = set(capital_records.keys())

    for trade_date, (available, position_val, total) in capital_records.items():
        existing = existing_by_date.get(trade_date)
        if existing is not None:
            existing.capital = total
            existing.available_funds = available
            existing.position_value = position_val
        else:
            db.add(
                StrategyCapitalHistory(
                    user_id=user_id,
                    strategy_id=strategy_id,
                    date=trade_date,
                    capital=total,
                    available_funds=available,
                    position_value=position_val,
                )
            )

    for record in existing_records:
        if record.date not in keep_dates:
            await db.delete(record)
    await db.commit()

async def recalculate_capital_history(db: AsyncSession, user_id: int, start_date: date):
    """
    根据交易记录重新计算资金历史曲线（同花顺模式）
    
    同花顺资金管理算法：
    1. 总资产 = 可用资金 + 持仓市值
    2. 开仓时：
       - 可用资金减少 = 买入价*手数 + 手续费
       - 持仓增加，持仓市值 = Σ(持仓股票数量 × 当前价格)
    3. 平仓时：
       - 可用资金增加 = 卖出金额 - 卖出手续费
       - 持仓减少，持仓市值重新计算
    4. 取消交易时：
       - 该交易不影响资金曲线
    
    这样，股票价格变化时，持仓市值变化，总资产也随之变化。
    """
    # 以 users.initial_capital / initial_capital_date 作为稳定锚点
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if user and user.initial_capital_date:
        start_date = user.initial_capital_date

    initial_capital = user.initial_capital if user and user.initial_capital is not None else 100000.0

    # 确保 start_date 的初始资金记录存在（但注意：后续可能被同日交易覆盖，这里只负责兜底）
    result = await db.execute(
        select(CapitalHistory).where(
            CapitalHistory.user_id == user_id,
            CapitalHistory.date == start_date
        )
    )
    initial_record = result.scalar_one_or_none()
    if not initial_record:
        initial_record = CapitalHistory(
            user_id=user_id,
            date=start_date,
            capital=initial_capital,
            available_funds=initial_capital,
            position_value=0.0
        )
        db.add(initial_record)
        await db.flush()
    
    # 获取所有交易记录（从start_date开始，包括开仓和平仓）
    # 策略回测：需要获取所有在start_date之后有开仓或平仓的交易
    result = await db.execute(
        select(Trade)
        .where(
            Trade.user_id == user_id,
            Trade.is_deleted == False,
            # 获取开仓时间或平仓时间在start_date之后的交易
            or_(
                func.date(Trade.open_time) >= start_date,
                and_(
                    Trade.status == "closed",
                    Trade.close_time.isnot(None),
                    func.date(Trade.close_time) >= start_date
                )
            )
        )
        .order_by(Trade.open_time.asc())
    )
    trades = result.scalars().all()
    
    # 创建交易事件列表（包括开仓和平仓），按时间排序
    trade_events = []
    for trade in trades:
        open_date = trade.open_time.date()
        # 开仓事件（如果开仓日期 >= start_date）
        if open_date >= start_date:
            trade_events.append({
                'date': open_date,
                'time': trade.open_time,
                'type': 'open',
                'trade': trade
            })
        
        # 平仓事件（如果平仓日期 >= start_date）
        if trade.sell_price is not None:
            close_dt = trade.close_time or trade.updated_at or trade.open_time
            if close_dt is not None and trade.open_time is not None and close_dt < trade.open_time:
                close_dt = trade.open_time
            if close_dt is not None:
                close_date = close_dt.date()
                if close_date >= start_date:
                    trade_events.append({
                        'date': close_date,
                        'time': close_dt,
                        'type': 'close',
                        'trade': trade
                    })
    
    # 按时间排序所有事件（同花顺模式）
    trade_events.sort(key=lambda x: (x['date'], x['time']))
    
    # 同花顺资金管理：维护可用资金和持仓列表
    available_funds = initial_capital  # 可用资金
    positions = {}  # 当前持仓：{trade_id: trade}
    capital_records = {}  # 记录每日资金：{date: (available_funds, position_value, total_assets)}
    
    # 初始资金记录
    capital_records[start_date] = (initial_capital, 0.0, initial_capital)
    
    # 如果没有交易记录，只保留初始资金记录（强制恢复为初始入金）
    if not trade_events:
        # 删除除 start_date 之外的所有资金历史记录
        result = await db.execute(
            select(CapitalHistory).where(
                CapitalHistory.user_id == user_id,
                CapitalHistory.date != start_date
            )
        )
        records_to_delete = result.scalars().all()
        for record in records_to_delete:
            await db.delete(record)

        # 强制把 start_date 记录恢复为“初始入金”
        initial_record.capital = initial_capital
        initial_record.available_funds = initial_capital
        initial_record.position_value = 0.0

        await db.commit()
        return
    
    # 按时间顺序处理所有交易事件（同花顺模式）
    for event in trade_events:
        trade_date = event['date']
        trade = event['trade']
        
        if event['type'] == 'open':
            # 开仓：可用资金减少 = 买入价*手数 + 买入手续费
            # 优先使用buy_commission，如果没有则使用commission（兼容旧数据）
            buy_commission = trade.buy_commission if trade.buy_commission is not None else (trade.commission or 0)
            cost = trade.buy_price * trade.shares + buy_commission
            available_funds -= cost
            # 持仓增加
            positions[trade.id] = trade
            
        elif event['type'] == 'close' and trade.sell_price:
            # 平仓：可用资金增加 = 卖出金额 - 卖出手续费
            sell_amount = trade.sell_price * trade.shares
            # 计算卖出手续费
            if trade.profit_loss is not None:
                # 如果有profit_loss，说明已经计算过盈亏
                # profit_loss = 卖出金额 - 买入成本 - 总手续费
                # 其中：买入成本 = 买入价*手数 + 买入手续费
                #      总手续费 = 买入手续费 + 卖出手续费
                # 所以：profit_loss = 卖出金额 - (买入价*手数 + 买入手续费) - (买入手续费 + 卖出手续费)
                #      = 卖出金额 - 买入价*手数 - 买入手续费 - 买入手续费 - 卖出手续费
                #      = 卖出金额 - 买入价*手数 - 2*买入手续费 - 卖出手续费
                # 
                # 可用资金增加 = 卖出金额 - 卖出手续费
                # 开仓时扣除了：买入价*手数 + 买入手续费
                # 所以：可用资金增加 = (卖出金额 - 卖出手续费) - (买入价*手数 + 买入手续费) + (买入价*手数 + 买入手续费)
                #      = 卖出金额 - 卖出手续费
                # 
                # 从profit_loss反推：
                # profit_loss = 卖出金额 - 买入价*手数 - 买入手续费 - 卖出手续费
                # 卖出金额 = profit_loss + 买入价*手数 + 买入手续费 + 卖出手续费
                # 可用资金增加 = 卖出金额 - 卖出手续费 = profit_loss + 买入价*手数 + 买入手续费
                # 
                # 更简单的方法：开仓时扣除了 buy_cost = 买入价*手数 + 买入手续费
                # 平仓时应该增加 = 卖出金额 - 卖出手续费
                # 净变化 = (卖出金额 - 卖出手续费) - (买入价*手数 + 买入手续费) = profit_loss
                # 所以：可用资金增加 = buy_cost + profit_loss
                buy_commission = trade.buy_commission if trade.buy_commission is not None else (trade.commission or 0)
                buy_cost = trade.buy_price * trade.shares + buy_commission
                available_funds += buy_cost + trade.profit_loss
            else:
                # 如果没有profit_loss，计算卖出手续费
                # 优先使用已保存的卖出手续费
                if trade.sell_commission is not None:
                    sell_commission = trade.sell_commission
                else:
                    sell_commission = default_calculator.calculate_sell_commission(
                        trade.sell_price,
                        trade.shares,
                        trade.stock_code
                    )
                available_funds += sell_amount - sell_commission
            
            # 持仓减少
            if trade.id in positions:
                del positions[trade.id]
        
        # 计算持仓市值（历史回测模式：使用买入价作为持仓成本）
        # 注意：历史回测时不知道每天的实时价格，所以使用买入价作为保守估计
        position_value = 0.0
        for pos_trade in positions.values():
            # 历史资金曲线：使用买入价（持仓成本）
            position_value += pos_trade.buy_price * pos_trade.shares
        
        # 计算总资产 = 可用资金 + 持仓成本
        total_assets = available_funds + position_value
        
        # 记录该日期的资金（历史回测模式）
        # 如果同一天有多个交易，只记录最后一次的资金（最终资金）
        capital_records[trade_date] = (available_funds, position_value, total_assets)
    
    # 更新或创建资金历史记录（同花顺模式：记录可用资金、持仓市值、总资产）
    existing_result = await db.execute(
        select(CapitalHistory).where(
            CapitalHistory.user_id == user_id,
            CapitalHistory.date >= start_date,
        )
    )
    existing_records = existing_result.scalars().all()
    existing_by_date: dict[date, CapitalHistory] = {r.date: r for r in existing_records}

    keep_dates = set(capital_records.keys())

    for trade_date, (available, position_val, total) in capital_records.items():
        existing = existing_by_date.get(trade_date)
        if existing is not None:
            existing.capital = total
            existing.available_funds = available
            existing.position_value = position_val
        else:
            db.add(
                CapitalHistory(
                    user_id=user_id,
                    date=trade_date,
                    capital=total,
                    available_funds=available,
                    position_value=position_val,
                )
            )

    for record in existing_records:
        if record.date not in keep_dates:
            await db.delete(record)
    
    await db.commit()

async def _ensure_strategy_capital_history_uptodate(db: AsyncSession, user_id: int, strategy_id: int) -> None:
    latest_result = await db.execute(
        select(StrategyCapitalHistory)
        .where(
            StrategyCapitalHistory.user_id == user_id,
            StrategyCapitalHistory.strategy_id == strategy_id,
        )
        .order_by(StrategyCapitalHistory.date.desc())
        .limit(1)
    )
    latest = latest_result.scalar_one_or_none()

    last_trade_dt_result = await db.execute(
        select(func.max(Trade.open_time), func.max(Trade.close_time)).where(
            Trade.user_id == user_id,
            Trade.strategy_id == strategy_id,
            Trade.is_deleted == False,
        )
    )
    max_open_dt, max_close_dt = last_trade_dt_result.one()
    last_event_date: date | None = None
    for dt in (max_open_dt, max_close_dt):
        if dt is None:
            continue
        d = dt.date()
        if last_event_date is None or d > last_event_date:
            last_event_date = d

    if last_event_date is None and latest is None:
        return

    should_recalc = False
    if latest is None:
        should_recalc = True
    elif last_event_date is not None and latest.date < last_event_date:
        should_recalc = True
    else:
        open_positions_result = await db.execute(
            select(func.count(Trade.id)).where(
                Trade.user_id == user_id,
                Trade.strategy_id == strategy_id,
                Trade.is_deleted == False,
                Trade.status == "open",
                Trade.close_time.is_(None),
                Trade.sell_price.is_(None),
            )
        )
        open_count = int(open_positions_result.scalar() or 0)
        latest_pos_val = float(latest.position_value or 0.0) if latest is not None else 0.0
        if open_count == 0 and latest_pos_val > 1e-6:
            should_recalc = True
        if not should_recalc and latest is not None and latest.created_at is not None:
            last_updated_result = await db.execute(
                select(func.max(Trade.updated_at)).where(
                    Trade.user_id == user_id,
                    Trade.strategy_id == strategy_id,
                    Trade.is_deleted == False,
                )
            )
            last_updated = last_updated_result.scalar()
            if last_updated is not None and last_updated > latest.created_at:
                should_recalc = True

    if not should_recalc:
        return

    start_date = latest.date if latest is not None else (last_event_date or date.today())
    await recalculate_strategy_capital_history(db, user_id, strategy_id, start_date)

@router.get("/strategies", response_model=list[StrategyResponse], summary="获取策略列表")
async def list_strategies(
    market: str = "stock",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Strategy)
        .where(
            Strategy.user_id == current_user.id,
            Strategy.market == market,
            Strategy.name != "默认策略" if market == "stock" else True,
        )
        .order_by(Strategy.created_at.asc())
    )
    strategies = result.scalars().all()
    return [
        StrategyResponse(
            id=s.id,
            user_id=s.user_id,
            name=s.name,
            uid=s.uid,
            market=s.market,
            initial_capital=s.initial_capital,
            initial_date=s.initial_date,
            created_at=s.created_at,
        )
        for s in strategies
    ]

@router.post("/strategies", response_model=StrategyResponse, summary="创建策略")
async def create_strategy(
    payload: StrategyCreate,
    market: str = "stock",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="策略名称不能为空")

    initial_capital = float(current_user.initial_capital) if current_user.initial_capital is not None else 100000.0
    initial_date = current_user.initial_capital_date or date.today()

    strategy = Strategy(
        user_id=current_user.id,
        name=name,
        uid=str(uuid.uuid4()),
        market=market,
        initial_capital=initial_capital,
        initial_date=initial_date,
    )
    db.add(strategy)
    await db.flush()

    if market == "stock":
        db.add(
            StrategyCapitalHistory(
                user_id=current_user.id,
                strategy_id=strategy.id,
                date=initial_date,
                capital=initial_capital,
                available_funds=initial_capital,
                position_value=0.0,
            )
        )
    await db.commit()
    await db.refresh(strategy)

    if market == "stock":
        await _migrate_legacy_stock_data_to_strategy(db, current_user, strategy)
    if market == "forex":
        await _migrate_legacy_forex_data_to_strategy(db, current_user, strategy)

    return StrategyResponse(
        id=strategy.id,
        user_id=strategy.user_id,
        name=strategy.name,
        uid=strategy.uid,
        market=strategy.market,
        initial_capital=strategy.initial_capital,
        initial_date=strategy.initial_date,
        created_at=strategy.created_at,
    )

@router.delete("/strategies", summary="删除所有策略")
async def delete_all_strategies(
    market: str = "stock",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    删除指定市场的所有策略（软删除关联数据，物理删除策略记录）
    """
    # 1. 查找该市场下的所有策略
    result = await db.execute(
        select(Strategy).where(
            Strategy.user_id == current_user.id,
            Strategy.market == market
        )
    )
    strategies = result.scalars().all()
    
    deleted_count = 0
    
    for strategy in strategies:
        # 删除关联数据逻辑与单个删除相同
        if market == "stock":
            trades_result = await db.execute(
                select(Trade).where(
                    Trade.user_id == current_user.id,
                    Trade.strategy_id == strategy.id
                )
            )
            trades = trades_result.scalars().all()
            for t in trades:
                t.is_deleted = True
                t.deleted_at = datetime.now()
            
            # 删除策略资金历史
            capital_result = await db.execute(
                select(StrategyCapitalHistory).where(
                    StrategyCapitalHistory.user_id == current_user.id,
                    StrategyCapitalHistory.strategy_id == strategy.id
                )
            )
            for h in capital_result.scalars().all():
                await db.delete(h)
                
        elif market == "forex":
            trades_result = await db.execute(
                select(ForexTrade).where(
                    ForexTrade.user_id == current_user.id,
                    ForexTrade.strategy_id == strategy.id
                )
            )
            trades = trades_result.scalars().all()
            for t in trades:
                t.is_deleted = True
                t.deleted_at = datetime.now()
                
        # 删除策略本身
        await db.delete(strategy)
        deleted_count += 1
        
    await db.commit()
    
    return {"message": f"已删除 {deleted_count} 个策略", "deleted_count": deleted_count}

@router.delete("/strategies/{strategy_id}", summary="删除策略")
async def delete_strategy(
    strategy_id: int,
    market: str = "stock",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    strategy_result = await db.execute(
        select(Strategy).where(
            Strategy.id == strategy_id,
            Strategy.user_id == current_user.id,
            Strategy.market == market,
        )
    )
    strategy = strategy_result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")

    deleted_trades = 0

    if market == "stock":
        trades_result = await db.execute(
            select(Trade).where(
                Trade.user_id == current_user.id,
                Trade.strategy_id == strategy.id,
                Trade.is_deleted == False,
            )
        )
        trades = trades_result.scalars().all()
        for t in trades:
            t.is_deleted = True
            t.updated_at = datetime.utcnow()
        deleted_trades = len(trades)

        history_result = await db.execute(
            select(StrategyCapitalHistory).where(
                StrategyCapitalHistory.user_id == current_user.id,
                StrategyCapitalHistory.strategy_id == strategy.id,
            )
        )
        history = history_result.scalars().all()
        for h in history:
            await db.delete(h)

        await db.delete(strategy)
        await db.commit()
        return {"message": "删除成功", "deleted_trades": deleted_trades}

    if market == "forex":
        now = datetime.utcnow()
        trades_result = await db.execute(
            select(ForexTrade).where(
                ForexTrade.user_id == current_user.id,
                ForexTrade.strategy_id == strategy.id,
                ForexTrade.is_deleted == False,
            )
        )
        trades = trades_result.scalars().all()
        for t in trades:
            t.is_deleted = True
            t.updated_at = now
        deleted_trades = len(trades)

        await db.delete(strategy)
        await db.commit()
        return {"message": "删除成功", "deleted_trades": deleted_trades}

    raise HTTPException(status_code=400, detail="不支持的市场类型")

@router.get("/strategies/capital-histories", summary="获取全部策略资金曲线（对比）")
async def get_all_strategy_capital_histories(
    start_date: date | None = None,
    end_date: date | None = None,
    market: str = "stock",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if market not in ("stock", "forex"):
        return {"market": market, "baseline": None, "series_by_strategy_id": {}, "strategies": []}
    baseline = float(current_user.initial_capital) if current_user.initial_capital is not None else 100000.0

    if market == "forex":
        acc_result = await db.execute(
            select(ForexAccount).where(ForexAccount.user_id == current_user.id)
        )
        account = acc_result.scalar_one_or_none()
        baseline = float(getattr(account, "initial_balance", None) or 10000.0)
        anchor_date: date = getattr(account, "initial_date", None) or datetime.utcnow().date()

        strat_result = await db.execute(
            select(Strategy)
            .where(
                Strategy.user_id == current_user.id,
                Strategy.market == "forex",
            )
            .order_by(Strategy.created_at.asc())
        )
        strategies = strat_result.scalars().all()

        series_by_strategy_id: dict[int, list[dict]] = {}
        for s in strategies:
            trades_result = await db.execute(
                select(ForexTrade).where(
                    ForexTrade.user_id == current_user.id,
                    ForexTrade.strategy_id == s.id,
                    ForexTrade.is_deleted == False,
                ).order_by(ForexTrade.open_time.asc())
            )
            trades = trades_result.scalars().all()

            strategy_baseline = float(s.initial_capital) if s.initial_capital is not None else baseline
            strategy_anchor_date = s.initial_date or anchor_date

            effective_start = strategy_anchor_date
            if start_date is not None and start_date > effective_start:
                effective_start = start_date

            if end_date is not None and effective_start > end_date:
                series_by_strategy_id[s.id] = []
                continue

            running = strategy_baseline
            start_value = strategy_baseline
            points_by_date: dict[date, float] = {effective_start: start_value}

            events: list[tuple[datetime, str, ForexTrade]] = []
            for t in trades:
                if t.open_time is not None:
                    events.append((t.open_time, "open", t))
                if t.status == "closed" and t.close_time is not None:
                    events.append((t.close_time, "close", t))
            events.sort(key=lambda x: x[0])

            for event_time, event_type, t in events:
                beijing_date = (event_time + timedelta(hours=8)).date()
                if beijing_date < strategy_anchor_date:
                    continue
                if end_date is not None and beijing_date > end_date:
                    break
                if event_type == "open":
                    running -= float(t.commission or 0)
                else:
                    running += float(t.profit or 0) + float(t.commission or 0)
                if beijing_date < effective_start:
                    start_value = running
                    points_by_date[effective_start] = start_value
                    continue
                points_by_date[beijing_date] = running

            dates = sorted(points_by_date.keys())
            series_by_strategy_id[s.id] = [
                {
                    "date": d.isoformat(),
                    "equity": float(points_by_date[d]),
                    "balance": float(points_by_date[d]),
                }
                for d in dates
            ]

        return {
            "market": "forex",
            "baseline": baseline,
            "anchor_date": anchor_date.isoformat() if anchor_date else None,
            "strategies": [
                {
                    "id": s.id,
                    "name": s.name,
                    "uid": s.uid,
                    "initial_capital": float(s.initial_capital) if s.initial_capital is not None else None,
                    "initial_date": s.initial_date.isoformat() if s.initial_date else None,
                }
                for s in strategies
            ],
            "series_by_strategy_id": series_by_strategy_id,
        }

    strat_result = await db.execute(
        select(Strategy)
        .where(
            Strategy.user_id == current_user.id,
            Strategy.market == "stock",
            Strategy.name != "默认策略",
        )
        .order_by(Strategy.created_at.asc())
    )
    strategies = strat_result.scalars().all()

    series_by_strategy_id: dict[int, list[dict]] = {}
    for s in strategies:
        q = select(StrategyCapitalHistory).where(
            StrategyCapitalHistory.user_id == current_user.id,
            StrategyCapitalHistory.strategy_id == s.id,
        )
        if start_date:
            q = q.where(StrategyCapitalHistory.date >= start_date)
        if end_date:
            q = q.where(StrategyCapitalHistory.date <= end_date)
        q = q.order_by(StrategyCapitalHistory.date.asc())
        r = await db.execute(q)
        history = r.scalars().all()
        series_by_strategy_id[s.id] = [
            {
                "date": h.date.isoformat(),
                "capital": float(h.capital),
                "available_funds": float(h.available_funds) if h.available_funds is not None else None,
                "position_value": float(h.position_value) if h.position_value is not None else 0.0,
            }
            for h in history
        ]

    return {
        "market": "stock",
        "baseline": baseline,
        "strategies": [
            {
                "id": s.id,
                "name": s.name,
                "uid": s.uid,
                "initial_capital": float(s.initial_capital) if s.initial_capital is not None else None,
                "initial_date": s.initial_date.isoformat() if s.initial_date else None,
            }
            for s in strategies
        ],
        "series_by_strategy_id": series_by_strategy_id,
    }
