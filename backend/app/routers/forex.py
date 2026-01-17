from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from datetime import datetime, date, timezone, timedelta
import asyncio
import time
import aiohttp

from app.database import get_db, User, ForexAccount, ForexTrade, Strategy, AsyncSessionLocal
from app.middleware.auth import get_current_user
from app.routers.user import _get_forex_strategy
from app.models import (
    ForexAccountResponse,
    ForexAccountUpdate,
    ForexAccountReset,
    ForexAccountInitialUpdate,
    ForexTradeCreate,
    ForexTradeUpdate,
    ForexTradeClose,
    ForexTradeResponse,
    ForexPaginatedTradeResponse,
    ForexCapitalPoint,
    ForexQuoteResponse,
)

router = APIRouter()


def _contract_size(symbol: str) -> float:
    if symbol.upper() == "XAUUSD":
        return 100.0
    return 100000.0


def _calc_profit(symbol: str, side: str, lots: float, open_price: float, close_price: float) -> float:
    side_upper = side.upper()
    diff = close_price - open_price if side_upper == "BUY" else open_price - close_price
    return diff * lots * _contract_size(symbol)

def _calc_margin(positions: list[ForexTrade], leverage: float) -> float:
    lev = float(leverage or 0)
    if lev <= 0:
        return 0.0
    margin = 0.0
    for p in positions:
        if p.open_price is None or p.open_price <= 0:
            continue
        if p.lots is None or p.lots <= 0:
            continue
        notional = float(p.open_price) * float(p.lots) * float(_contract_size(p.symbol))
        margin += notional / lev
    return margin

_fx_quote_cache: dict[tuple[str, str], tuple[float, float, str]] = {}
_FX_QUOTE_TTL_SECONDS = 2.0


def _normalize_fx_symbol(symbol: str) -> str:
    return symbol.strip().upper().replace("/", "")


async def _fetch_fx_mid_price(symbol: str) -> tuple[float, str]:
    sym = _normalize_fx_symbol(symbol)
    if len(sym) != 6 or not sym.isalpha():
        raise ValueError("Unsupported symbol format")
    base = sym[:3]
    quote = sym[3:]

    cache_key = (base, quote)
    now_ts = time.time()
    cached = _fx_quote_cache.get(cache_key)
    if cached is not None:
        mid, ts, source = cached
        if now_ts - ts <= _FX_QUOTE_TTL_SECONDS:
            return mid, source

    url = f"https://open.er-api.com/v6/latest/{base}"
    async with aiohttp.ClientSession() as session:
        # Disable SSL verification to avoid local certificate issues
        async with session.get(url, ssl=False, timeout=aiohttp.ClientTimeout(total=3)) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Quote fetch failed: HTTP {resp.status}")
            data = await resp.json()

    rates = data.get("rates") or {}
    if quote not in rates:
        raise ValueError("Unsupported quote currency")
    mid = float(rates[quote])
    source = "ExchangeRate-API (open.er-api.com)"
    _fx_quote_cache[cache_key] = (mid, now_ts, source)
    return mid, source


async def _get_or_create_account(db: AsyncSession, user_id: int) -> ForexAccount:
    try:
        result = await db.execute(select(ForexAccount).where(ForexAccount.user_id == user_id))
        account = result.scalar_one_or_none()
        if account:
            return account

        now = datetime.utcnow()
        new_account = ForexAccount(
            user_id=user_id,
            currency="USD",
            leverage=100,
            initial_balance=10000,
            initial_date=now.date(),
            balance=10000,
            equity=10000,
            margin=0,
            free_margin=10000,
            margin_level=0,
            max_drawdown=0,
            peak_equity=10000,
        )
        db.add(new_account)
        await db.commit()
        await db.refresh(new_account)
        return new_account
    except Exception as e:
        # 如果出现唯一约束冲突，说明其他请求并发创建了账户
        # 此时尝试重新查询
        await db.rollback()
        result = await db.execute(select(ForexAccount).where(ForexAccount.user_id == user_id))
        account = result.scalar_one_or_none()
        if account:
            return account
        raise e


async def _recalculate_account(db: AsyncSession, user_id: int, strategy_id: int | None = None) -> ForexAccount:
    account = await _get_or_create_account(db, user_id)
    
    anchor_date = account.initial_date
    initial_balance = float(account.initial_balance or 0)

    if strategy_id is not None:
        strategy = await _get_forex_strategy(db, User(id=user_id), strategy_id)
        if strategy:
            anchor_date = strategy.initial_date or anchor_date
            if strategy.initial_capital is not None:
                initial_balance = float(strategy.initial_capital)

    result = await db.execute(
        select(ForexTrade)
        .where(
            ForexTrade.user_id == user_id,
            ForexTrade.is_deleted == False,
            ForexTrade.status == "closed",
            ForexTrade.close_time.isnot(None),
            ForexTrade.strategy_id == strategy_id if strategy_id is not None else True,
        )
        .order_by(ForexTrade.close_time.asc())
    )
    closed = result.scalars().all()

    running = initial_balance
    peak = running
    max_drawdown = 0.0

    for t in closed:
        if anchor_date is not None and t.close_time is not None and t.close_time.date() < anchor_date:
            continue
        if t.profit is None and t.close_price is not None:
            gross = _calc_profit(t.symbol, t.side, t.lots, t.open_price, t.close_price)
            t.profit = float(gross) - float(t.commission or 0) - float(t.swap or 0)
        running += float(t.profit or 0)
        peak = max(peak, running)
        dd = ((peak - running) / peak) * 100 if peak else 0.0
        max_drawdown = max(max_drawdown, dd)

    open_result = await db.execute(
        select(ForexTrade).where(
            ForexTrade.user_id == user_id,
            ForexTrade.is_deleted == False,
            ForexTrade.status == "open",
            ForexTrade.strategy_id == strategy_id if strategy_id is not None else True,
        )
    )
    open_positions = open_result.scalars().all()

    margin = _calc_margin(open_positions, float(account.leverage or 0))

    account.balance = running
    floating = 0.0
    for p in open_positions:
        try:
            current_price, _ = await _fetch_fx_mid_price(p.symbol)
        except Exception:
            continue
        gross = _calc_profit(p.symbol, p.side, float(p.lots or 0), float(p.open_price or 0), float(current_price))
        floating += float(gross) - float(p.commission or 0) - float(p.swap or 0)

    equity = running + floating
    account.equity = equity
    account.margin = margin
    account.free_margin = equity - margin
    account.margin_level = (equity / margin) * 100 if margin > 0 else 0
    account.peak_equity = max(peak, equity)
    account.max_drawdown = max_drawdown

    await db.commit()
    await db.refresh(account)
    return account


def _to_account_response(account: ForexAccount) -> ForexAccountResponse:
    return ForexAccountResponse(
        user_id=account.user_id,
        currency=account.currency,
        leverage=account.leverage,
        initial_balance=account.initial_balance,
        initial_date=account.initial_date,
        balance=account.balance,
        equity=account.equity,
        margin=account.margin,
        free_margin=account.free_margin,
        margin_level=account.margin_level,
        max_drawdown=account.max_drawdown,
        peak_equity=account.peak_equity,
        updated_at=account.updated_at,
    )


def _to_trade_response(trade: ForexTrade) -> ForexTradeResponse:
    # 计算风险回报比
    theoretical_rr = None
    actual_rr = None
    
    try:
        open_price = float(trade.open_price) if trade.open_price else 0.0
        sl_price = float(trade.sl) if trade.sl else None
        
        if sl_price is not None and open_price > 0 and abs(open_price - sl_price) > 1e-9:
            risk_per_unit = abs(open_price - sl_price)
            
            # 理论风险回报比
            if trade.tp is not None:
                tp_price = float(trade.tp)
                reward_per_unit = abs(tp_price - open_price)
                theoretical_rr = round(reward_per_unit / risk_per_unit, 2)
                
            # 实际风险回报比
            # 实际风险 = 单位风险 * 手数 * 合约大小
            # 实际回报 = 净利润 (profit)
            if trade.profit is not None:
                lots = float(trade.lots) if trade.lots else 0.0
                contract_size = _contract_size(trade.symbol)
                total_risk = risk_per_unit * lots * contract_size
                
                if total_risk > 1e-9:
                    actual_rr = round(float(trade.profit) / total_risk, 2)
    except Exception:
        pass

    return ForexTradeResponse(
        id=trade.id,
        user_id=trade.user_id,
        strategy_id=trade.strategy_id,
        symbol=trade.symbol,
        side=trade.side,
        lots=trade.lots,
        open_time=trade.open_time,
        close_time=trade.close_time,
        open_price=trade.open_price,
        close_price=trade.close_price,
        sl=trade.sl,
        tp=trade.tp,
        commission=trade.commission,
        swap=trade.swap,
        profit=trade.profit,
        notes=trade.notes,
        status=trade.status,
        theoretical_risk_reward_ratio=theoretical_rr,
        actual_risk_reward_ratio=actual_rr,
        created_at=trade.created_at,
        updated_at=trade.updated_at,
    )


@router.get("/account", response_model=ForexAccountResponse, summary="获取外汇账户信息")
async def get_account(
    strategy_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    strategy = await _get_forex_strategy(db, current_user, strategy_id)
    account = await _recalculate_account(db, current_user.id, strategy.id)
    return _to_account_response(account)


@router.get("/quotes", response_model=list[ForexQuoteResponse], summary="获取外汇实时行情（中间价）")
async def get_quotes(
    symbols: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items: list[ForexQuoteResponse] = []
    for raw in [s for s in symbols.split(",") if s.strip()]:
        sym = _normalize_fx_symbol(raw)
        asof = datetime.utcnow()
        try:
            mid, source = await _fetch_fx_mid_price(sym)
            items.append(
                ForexQuoteResponse(
                    symbol=sym,
                    price=mid,
                    bid=mid,
                    ask=mid,
                    asof=asof,
                    source=source,
                    error=None,
                )
            )
        except Exception as e:
            items.append(
                ForexQuoteResponse(
                    symbol=sym,
                    price=None,
                    bid=None,
                    ask=None,
                    asof=asof,
                    source="N/A",
                    error=str(e),
                )
            )
    return items


@router.patch("/account", response_model=ForexAccountResponse, summary="更新外汇账户配置")
async def update_account(
    payload: ForexAccountUpdate,
    strategy_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account = await _get_or_create_account(db, current_user.id)
    if payload.currency is not None:
        account.currency = payload.currency
    if payload.leverage is not None:
        account.leverage = payload.leverage
    if payload.balance is not None:
        account.balance = payload.balance
        account.equity = payload.balance
        account.free_margin = payload.balance
        account.peak_equity = max(account.peak_equity or payload.balance, payload.balance)
    await db.commit()
    account = await _recalculate_account(db, current_user.id, strategy_id)
    return _to_account_response(account)


@router.post("/account/initial", response_model=ForexAccountResponse, summary="设置外汇初始资金与起始日期（不清空交易）")
async def set_initial_capital(
    payload: ForexAccountInitialUpdate,
    strategy_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if strategy_id is not None:
        strategy = await _get_forex_strategy(db, current_user, strategy_id)
        strategy.initial_capital = payload.initial_balance
        if payload.initial_date is not None:
            strategy.initial_date = payload.initial_date
        await db.commit()
    else:
        account = await _get_or_create_account(db, current_user.id)
        account.initial_balance = payload.initial_balance
        if payload.initial_date is not None:
            account.initial_date = payload.initial_date
        await db.commit()

    await _recalculate_account(db, current_user.id, strategy_id)
    account = await _get_or_create_account(db, current_user.id)
    return _to_account_response(account)

@router.post("/account/reset", response_model=ForexAccountResponse, summary="重置外汇账户与交易数据")
async def reset_account(
    payload: ForexAccountReset,
    strategy_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account = await _get_or_create_account(db, current_user.id)
    if strategy_id is not None:
        await _get_forex_strategy(db, current_user, strategy_id)

    reset_date = payload.date or datetime.utcnow().date()
    account.currency = payload.currency or account.currency
    account.leverage = payload.leverage or account.leverage
    account.initial_balance = payload.balance
    account.initial_date = reset_date
    account.balance = payload.balance
    account.equity = payload.balance
    account.margin = 0
    account.free_margin = payload.balance
    account.margin_level = 0
    account.peak_equity = payload.balance
    account.max_drawdown = 0

    if strategy_id is not None:
        now = datetime.utcnow()
        await db.execute(
            update(ForexTrade)
            .where(
                ForexTrade.user_id == current_user.id,
                ForexTrade.strategy_id == strategy_id,
                ForexTrade.is_deleted == False,
            )
            .values(is_deleted=True, updated_at=now)
        )
        await db.commit()
        await db.refresh(account)
        account = await _recalculate_account(db, current_user.id, strategy_id)
        return _to_account_response(account)

    await db.execute(ForexTrade.__table__.delete().where(ForexTrade.user_id == current_user.id))
    await db.commit()
    await db.refresh(account)
    return _to_account_response(account)


@router.get("/positions", response_model=list[ForexTradeResponse], summary="获取外汇持仓")
async def get_positions(
    strategy_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    strategy = await _get_forex_strategy(db, current_user, strategy_id)
    result = await db.execute(
        select(ForexTrade)
        .where(
            ForexTrade.user_id == current_user.id,
            ForexTrade.strategy_id == strategy.id,
            ForexTrade.status == "open",
            ForexTrade.is_deleted == False,
        )
        .order_by(ForexTrade.open_time.desc())
    )
    items = result.scalars().all()
    return [_to_trade_response(t) for t in items]


@router.get("/trades", response_model=ForexPaginatedTradeResponse, summary="获取外汇交易账单（分页）")
async def get_trades(
    page: int = 1,
    page_size: int = 50,
    strategy_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    strategy = await _get_forex_strategy(db, current_user, strategy_id)
    count_result = await db.execute(
        select(func.count())
        .select_from(ForexTrade)
        .where(
            ForexTrade.user_id == current_user.id,
            ForexTrade.strategy_id == strategy.id,
            ForexTrade.is_deleted == False,
        )
    )
    total = int(count_result.scalar() or 0)
    offset = (page - 1) * page_size
    result = await db.execute(
        select(ForexTrade)
        .where(
            ForexTrade.user_id == current_user.id,
            ForexTrade.strategy_id == strategy.id,
            ForexTrade.is_deleted == False,
        )
        .order_by(ForexTrade.open_time.desc())
        .offset(offset)
        .limit(page_size)
    )
    items = result.scalars().all()
    total_pages = max(1, (total + page_size - 1) // page_size) if total else 0
    return ForexPaginatedTradeResponse(
        items=[_to_trade_response(t) for t in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )

@router.get("/trades/dates", response_model=list[str], summary="获取外汇有交易记录的日期列表")
async def get_trade_dates(
    strategy_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    strategy = await _get_forex_strategy(db, current_user, strategy_id)
    result = await db.execute(
        select(ForexTrade.open_time)
        .where(
            ForexTrade.user_id == current_user.id,
            ForexTrade.strategy_id == strategy.id,
            ForexTrade.is_deleted == False,
        )
        .order_by(ForexTrade.open_time.asc())
    )
    trade_times = result.scalars().all()
    date_set: set[date] = set()
    for trade_time in trade_times:
        if trade_time:
            beijing_time = trade_time + timedelta(hours=8)
            date_set.add(beijing_time.date())

    return [d.isoformat() for d in sorted(date_set)]


@router.post("/trades", response_model=ForexTradeResponse, status_code=status.HTTP_201_CREATED, summary="创建外汇开仓记录")
async def create_trade(
    payload: ForexTradeCreate,
    strategy_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    async def _recalculate_account_async(user_id: int, strategy_id_value: int):
        try:
            async with AsyncSessionLocal() as session:
                await _recalculate_account(session, user_id, strategy_id_value)
        except Exception:
            pass

    requested_strategy_id = payload.strategy_id if payload.strategy_id is not None else strategy_id
    strategy = await _get_forex_strategy(db, current_user, requested_strategy_id)
    open_time = payload.open_time
    if open_time is None:
        open_time = datetime.utcnow()
    elif open_time.tzinfo is not None:
        open_time = open_time.astimezone(timezone.utc).replace(tzinfo=None)

    trade = ForexTrade(
        user_id=current_user.id,
        strategy_id=strategy.id,
        symbol=payload.symbol.upper(),
        side=payload.side.upper(),
        lots=payload.lots,
        open_time=open_time,
        open_price=payload.open_price,
        sl=payload.sl,
        tp=payload.tp,
        commission=float(payload.commission or 0),
        swap=float(payload.swap or 0),
        notes=payload.notes,
        status="open",
        is_deleted=False,
    )
    db.add(trade)

    await db.commit()
    await db.refresh(trade)
    asyncio.create_task(_recalculate_account_async(current_user.id, strategy.id))
    return _to_trade_response(trade)

@router.delete("/trades/clear-all", summary="清空外汇交易记录（软删除）")
async def clear_all_trades(
    strategy_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    strategy = await _get_forex_strategy(db, current_user, strategy_id)
    now = datetime.utcnow()
    result = await db.execute(
        update(ForexTrade)
        .where(
            ForexTrade.user_id == current_user.id,
            ForexTrade.strategy_id == strategy.id,
            ForexTrade.is_deleted == False,
        )
        .values(is_deleted=True, updated_at=now)
    )
    await db.commit()
    await _recalculate_account(db, current_user.id, strategy.id)
    deleted_count = int(getattr(result, "rowcount", 0) or 0)
    return {"message": "清空成功", "deleted_count": deleted_count}


@router.patch("/trades/{trade_id}", response_model=ForexTradeResponse, summary="更新外汇交易记录")
async def update_trade(
    trade_id: int,
    payload: ForexTradeUpdate,
    strategy_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    strategy = await _get_forex_strategy(db, current_user, strategy_id)
    result = await db.execute(
        select(ForexTrade).where(
            ForexTrade.id == trade_id,
            ForexTrade.user_id == current_user.id,
            ForexTrade.strategy_id == strategy.id,
            ForexTrade.is_deleted == False,
        )
    )
    trade = result.scalar_one_or_none()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")

    if payload.sl is not None:
        trade.sl = payload.sl
    if payload.tp is not None:
        trade.tp = payload.tp
    if payload.notes is not None:
        trade.notes = payload.notes

    await db.commit()
    await db.refresh(trade)
    return _to_trade_response(trade)


@router.post("/trades/{trade_id}/close", response_model=ForexTradeResponse, summary="平仓外汇交易")
async def close_trade(
    trade_id: int,
    payload: ForexTradeClose,
    strategy_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    strategy = await _get_forex_strategy(db, current_user, strategy_id)
    result = await db.execute(
        select(ForexTrade).where(
            ForexTrade.id == trade_id,
            ForexTrade.user_id == current_user.id,
            ForexTrade.strategy_id == strategy.id,
            ForexTrade.is_deleted == False,
        )
    )
    trade = result.scalar_one_or_none()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    if trade.status != "open":
        raise HTTPException(status_code=400, detail="Trade is not open")

    close_time = payload.close_time
    if close_time is None:
        close_time = datetime.utcnow()
    elif close_time.tzinfo is not None:
        close_time = close_time.astimezone(timezone.utc).replace(tzinfo=None)

    trade.close_time = close_time
    trade.close_price = payload.close_price
    if payload.swap is not None:
        trade.swap = float(payload.swap)
    if payload.commission is not None:
        trade.commission = float(payload.commission)
    gross_profit = _calc_profit(trade.symbol, trade.side, trade.lots, trade.open_price, payload.close_price)
    net_profit = gross_profit - trade.commission - trade.swap
    trade.profit = net_profit
    trade.status = "closed"

    await db.commit()
    await db.refresh(trade)
    await _recalculate_account(db, current_user.id, strategy.id)
    return _to_trade_response(trade)


@router.delete("/trades/{trade_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除外汇交易记录（软删除）")
async def delete_trade(
    trade_id: int,
    strategy_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    strategy = await _get_forex_strategy(db, current_user, strategy_id)
    result = await db.execute(
        select(ForexTrade).where(
            ForexTrade.id == trade_id,
            ForexTrade.user_id == current_user.id,
            ForexTrade.strategy_id == strategy.id,
            ForexTrade.is_deleted == False,
        )
    )
    trade = result.scalar_one_or_none()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    trade.is_deleted = True
    await db.commit()
    await _recalculate_account(db, current_user.id, strategy.id)
    return


@router.get("/capital-history", response_model=list[ForexCapitalPoint], summary="获取外汇资金曲线")
async def get_capital_history(
    start_date: date | None = None,
    end_date: date | None = None,
    strategy_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    strategy = await _get_forex_strategy(db, current_user, strategy_id)
    account = await _get_or_create_account(db, current_user.id)
    anchor_date = account.initial_date or datetime.utcnow().date()
    if start_date is not None:
        anchor_date = max(anchor_date, start_date)

    result = await db.execute(
        select(ForexTrade)
        .where(
            ForexTrade.user_id == current_user.id,
            ForexTrade.strategy_id == strategy.id,
            ForexTrade.is_deleted == False,
            ForexTrade.status == "closed",
            ForexTrade.close_time.isnot(None),
        )
        .order_by(ForexTrade.close_time.asc())
    )
    closed = result.scalars().all()

    points_by_date: dict[date, float] = {}
    running = float(account.initial_balance)
    points_by_date[anchor_date] = running

    for t in closed:
        d = t.close_time.date() if t.close_time else anchor_date
        if d < anchor_date:
            continue
        running += float(t.profit or 0)
        points_by_date[d] = running

    dates = sorted(points_by_date.keys())
    points = [ForexCapitalPoint(date=d, equity=points_by_date[d], balance=points_by_date[d]) for d in dates]
    if end_date is not None:
        points = [p for p in points if p.date <= end_date]
    return points
