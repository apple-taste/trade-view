from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

from app.database import get_db, Trade, CapitalHistory
from app.middleware.auth import get_current_user
from app.models import PositionUpdate, TakeProfitRequest, StopLossRequest, TradeResponse
from app.database import User
from app.services.commission_calculator import default_calculator
from app.routers.user import recalculate_strategy_capital_history, _get_stock_strategy

router = APIRouter()

def _resolve_close_time(close_date: str | None) -> datetime:
    if close_date:
        try:
            date_obj = datetime.strptime(close_date, '%Y-%m-%d').date()
            beijing_tz = ZoneInfo('Asia/Shanghai')
            beijing_datetime = datetime.combine(date_obj, datetime.min.time().replace(hour=12)).replace(tzinfo=beijing_tz)
            return beijing_datetime.astimezone(ZoneInfo('UTC')).replace(tzinfo=None)
        except (ValueError, Exception):
            return datetime.utcnow()
    return datetime.utcnow()

def _validate_partial_close_shares(position_shares: int, requested_shares: int | None) -> int:
    shares_to_close = requested_shares if requested_shares is not None else position_shares
    if shares_to_close <= 0:
        raise HTTPException(status_code=400, detail="止盈/止损股数必须大于0")
    if shares_to_close > position_shares:
        raise HTTPException(status_code=400, detail="止盈/止损股数不能大于持仓股数")
    if shares_to_close % 100 != 0:
        raise HTTPException(status_code=400, detail="A股卖出股数必须是100的整数倍")
    return shares_to_close

async def update_capital_from_trade(db: AsyncSession, user_id: int, capital_change: float, trade_date: date):
    """
    根据交易更新资金历史
    
    Args:
        capital_change: 资金变化量
            - 开仓时：负数，表示扣除本金（买入价*手数 + 手续费）
            - 平仓时：正数或负数，表示盈亏（卖出价*手数 - 买入价*手数 - 手续费）
            注意：平仓时已经包含了本金回收，所以只需要加上盈亏即可
    """
    # 获取最新的资金记录
    result = await db.execute(
        select(CapitalHistory)
        .where(CapitalHistory.user_id == user_id)
        .order_by(CapitalHistory.date.desc())
        .limit(1)
    )
    latest_capital = result.scalar_one_or_none()
    
    if latest_capital:
        # 计算新资金 = 最新资金 + 变化量
        new_capital = latest_capital.capital + capital_change
    else:
        # 如果没有历史记录，使用默认值10万
        new_capital = 100000.0 + capital_change
    
    # 检查该日期是否已有记录
    result = await db.execute(
        select(CapitalHistory).where(
            CapitalHistory.user_id == user_id,
            CapitalHistory.date == trade_date
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        # 更新现有记录
        existing.capital = new_capital
    else:
        # 创建新记录
        new_history = CapitalHistory(
            user_id=user_id,
            date=trade_date,
            capital=new_capital
        )
        db.add(new_history)

@router.get(
    "",
    response_model=list[TradeResponse],
    summary="获取所有持仓",
    description="""
    获取当前用户的所有持仓（未平仓的交易记录）。
    
    返回的持仓信息包括：
    - 股票代码和名称
    - 买入价格和当前价格
    - 持仓股数
    - 持仓天数（自动计算）
    - 止损止盈价格和提醒设置
    
    持仓按开仓时间倒序排列。
    """,
    responses={
        200: {"description": "成功返回持仓列表"}
    }
)
async def get_positions(
    strategy_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    strategy = await _get_stock_strategy(db, current_user, strategy_id)
    result = await db.execute(
        select(Trade)
        .where(
            Trade.user_id == current_user.id,
            Trade.strategy_id == strategy.id,
            Trade.status == "open",
            Trade.is_deleted == False  # 排除已删除的记录
        )
        .order_by(Trade.open_time.desc())
    )
    positions = result.scalars().all()
    
    from app.services.price_monitor import price_monitor

    for position in positions:
        if position.open_time:
            days = (datetime.utcnow() - position.open_time).days
            position.holding_days = days
        
        if position.stock_code:
            cached_price, cached_source = price_monitor.get_current_price(position.stock_code)
            if cached_price is not None:
                position.current_price = float(cached_price)
                position.price_source = cached_source or "缓存"
            else:
                position.current_price = position.buy_price
                position.price_source = "成本价"
    
    # 扩展TradeResponse以包含price_source
    result = []
    for pos in positions:
        pos_dict = pos.__dict__.copy()
        if getattr(pos, "price_source", None):
            pos_dict["price_source"] = getattr(pos, "price_source", None)
        result.append(TradeResponse(**pos_dict))
    
    return result

@router.put("/{position_id}", response_model=TradeResponse)
async def update_position(
    position_id: int,
    position_data: PositionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Trade).where(
            Trade.id == position_id,
            Trade.user_id == current_user.id,
            Trade.status == "open",
            Trade.is_deleted == False  # 排除已删除的记录
        )
    )
    position = result.scalar_one_or_none()
    
    if not position:
        raise HTTPException(status_code=404, detail="持仓不存在或已平仓")
    
    # 更新字段
    update_data = position_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(position, key, value)
    
    # 更新持仓天数
    if position.open_time:
        position.holding_days = (datetime.utcnow() - position.open_time).days
    
    position.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(position)
    
    # 计算风险回报比
    pos_dict = position.__dict__.copy()
    if position.buy_price and position.stop_loss_price and position.take_profit_price:
        risk = position.buy_price - position.stop_loss_price
        reward = position.take_profit_price - position.buy_price
        if risk > 0:
            pos_dict['risk_reward_ratio'] = round(reward / risk, 2)
        else:
            pos_dict['risk_reward_ratio'] = None
    else:
        pos_dict['risk_reward_ratio'] = None
    
    return TradeResponse(**pos_dict)

@router.post(
    "/{position_id}/take-profit",
    response_model=TradeResponse,
    summary="执行止盈",
    description="""
    对指定持仓执行止盈操作。
    
    - **position_id**: 持仓ID（路径参数）
    - **sell_price**: 离场价格（请求体）
    
    执行后：
    1. 更新交易记录的离场价格和离场时间
    2. 将订单结果标记为"止盈"
    3. 将状态改为"closed"（已平仓）
    4. 该持仓将从持仓列表中移除
    
    注意：只能对未平仓的持仓执行此操作。
    """,
    responses={
        200: {"description": "止盈操作成功"},
        404: {"description": "持仓不存在或已平仓"}
    }
)
async def take_profit(
    position_id: int,
    request: TakeProfitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Trade).where(
            Trade.id == position_id,
            Trade.user_id == current_user.id,
            Trade.status == "open",
            Trade.is_deleted == False  # 排除已删除的记录
        )
    )
    position = result.scalar_one_or_none()
    
    if not position:
        raise HTTPException(status_code=404, detail="持仓不存在、已平仓或已被删除")
    
    close_time = _resolve_close_time(request.close_date)

    if position.open_time and close_time < position.open_time:
        close_time = position.open_time
    
    holding_days = (close_time - position.open_time).days if position.open_time else 0

    shares_to_close = _validate_partial_close_shares(position.shares, request.shares)
    
    # 计算卖出手续费（包括佣金、印花税、过户费）
    sell_commission = default_calculator.calculate_sell_commission(
        request.sell_price,
        shares_to_close,
        position.stock_code
    )
    
    # 总手续费 = 买入手续费 + 卖出手续费
    original_buy_commission = position.buy_commission or 0
    closed_buy_commission = original_buy_commission if shares_to_close == position.shares else round(original_buy_commission * (shares_to_close / position.shares), 6)
    total_commission = closed_buy_commission + sell_commission
    
    # 计算盈亏：卖出价*手数 - 买入价*手数 - 总手续费
    profit_loss = (request.sell_price - position.buy_price) * shares_to_close - total_commission
    
    # 计算实际风险回报比（止盈单）
    # 实际风险回报比 = (实际离场价 - 入场价) / (入场价 - 止损价)
    actual_rrr = None
    if position.buy_price and position.stop_loss_price and request.sell_price:
        risk = position.buy_price - position.stop_loss_price
        actual_reward = request.sell_price - position.buy_price  # 使用实际离场价
        if risk > 0:
            actual_rrr = round(actual_reward / risk, 2)

    if shares_to_close == position.shares:
        position.close_time = close_time
        position.sell_price = request.sell_price
        position.status = "closed"
        position.order_result = "止盈"
        position.holding_days = holding_days
        position.profit_loss = profit_loss
        position.sell_commission = sell_commission
        position.commission = total_commission
        position.actual_risk_reward_ratio = actual_rrr
        position.updated_at = close_time

        await db.commit()
        await db.refresh(position)

        strategy = await _get_stock_strategy(db, current_user, position.strategy_id)
        start_date = position.open_time.date() if position.open_time else close_time.date()
        await recalculate_strategy_capital_history(db, current_user.id, strategy.id, start_date)

        pos_dict = position.__dict__.copy()
        if position.buy_price and position.stop_loss_price and position.take_profit_price:
            risk = position.buy_price - position.stop_loss_price
            reward = position.take_profit_price - position.buy_price
            if risk > 0:
                pos_dict['risk_reward_ratio'] = round(reward / risk, 2)
            else:
                pos_dict['risk_reward_ratio'] = None
        else:
            pos_dict['risk_reward_ratio'] = None

        return TradeResponse(**pos_dict)

    remaining_shares = position.shares - shares_to_close
    remaining_buy_commission = round(original_buy_commission - closed_buy_commission, 6)

    closed_trade = Trade(
        user_id=position.user_id,
        strategy_id=position.strategy_id,
        stock_code=position.stock_code,
        stock_name=position.stock_name,
        open_time=position.open_time,
        close_time=close_time,
        shares=shares_to_close,
        commission=total_commission,
        buy_commission=closed_buy_commission,
        sell_commission=sell_commission,
        buy_price=position.buy_price,
        sell_price=request.sell_price,
        stop_loss_price=position.stop_loss_price,
        take_profit_price=position.take_profit_price,
        stop_loss_alert=position.stop_loss_alert,
        take_profit_alert=position.take_profit_alert,
        holding_days=holding_days,
        order_result="止盈",
        profit_loss=profit_loss,
        theoretical_risk_reward_ratio=position.theoretical_risk_reward_ratio,
        actual_risk_reward_ratio=actual_rrr,
        notes=position.notes or "",
        status="closed",
    )

    position.shares = remaining_shares
    position.buy_commission = remaining_buy_commission
    position.commission = remaining_buy_commission
    position.updated_at = close_time

    db.add(closed_trade)

    await db.commit()
    await db.refresh(closed_trade)
    
    strategy = await _get_stock_strategy(db, current_user, position.strategy_id)
    start_date = position.open_time.date() if position.open_time else close_time.date()
    await recalculate_strategy_capital_history(db, current_user.id, strategy.id, start_date)
    
    trade_dict = closed_trade.__dict__.copy()
    trade_dict['risk_reward_ratio'] = closed_trade.theoretical_risk_reward_ratio
    trade_dict['theoretical_risk_reward_ratio'] = closed_trade.theoretical_risk_reward_ratio
    trade_dict['actual_risk_reward_ratio'] = closed_trade.actual_risk_reward_ratio

    return TradeResponse(**trade_dict)

@router.post(
    "/{position_id}/stop-loss",
    response_model=TradeResponse,
    summary="执行止损",
    description="""
    对指定持仓执行止损操作。
    
    - **position_id**: 持仓ID（路径参数）
    - **sell_price**: 离场价格（请求体）
    
    执行后：
    1. 更新交易记录的离场价格和离场时间
    2. 将订单结果标记为"止损"
    3. 将状态改为"closed"（已平仓）
    4. 该持仓将从持仓列表中移除
    
    注意：只能对未平仓的持仓执行此操作。
    """,
    responses={
        200: {"description": "止损操作成功"},
        404: {"description": "持仓不存在或已平仓"}
    }
)
async def stop_loss(
    position_id: int,
    request: StopLossRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Trade).where(
            Trade.id == position_id,
            Trade.user_id == current_user.id,
            Trade.status == "open",
            Trade.is_deleted == False  # 排除已删除的记录
        )
    )
    position = result.scalar_one_or_none()
    
    if not position:
        raise HTTPException(status_code=404, detail="持仓不存在、已平仓或已被删除")
    
    close_time = _resolve_close_time(request.close_date)

    if position.open_time and close_time < position.open_time:
        close_time = position.open_time
    
    holding_days = (close_time - position.open_time).days if position.open_time else 0

    shares_to_close = _validate_partial_close_shares(position.shares, request.shares)
    
    # 计算卖出手续费（包括佣金、印花税、过户费）
    sell_commission = default_calculator.calculate_sell_commission(
        request.sell_price,
        shares_to_close,
        position.stock_code
    )
    
    # 总手续费 = 买入手续费 + 卖出手续费
    original_buy_commission = position.buy_commission or 0
    closed_buy_commission = original_buy_commission if shares_to_close == position.shares else round(original_buy_commission * (shares_to_close / position.shares), 6)
    total_commission = closed_buy_commission + sell_commission
    
    # 计算盈亏：卖出价*手数 - 买入价*手数 - 总手续费
    profit_loss = (request.sell_price - position.buy_price) * shares_to_close - total_commission
    
    # 计算实际风险回报比（止损单）
    # 实际风险回报比 = (止盈价 - 入场价) / (入场价 - 实际离场价)
    actual_rrr = None
    if position.buy_price and position.take_profit_price and request.sell_price:
        actual_risk = position.buy_price - request.sell_price  # 使用实际离场价
        theoretical_reward = position.take_profit_price - position.buy_price
        if actual_risk > 0:
            actual_rrr = round(theoretical_reward / actual_risk, 2)

    if shares_to_close == position.shares:
        position.close_time = close_time
        position.sell_price = request.sell_price
        position.status = "closed"
        position.order_result = "止损"
        position.holding_days = holding_days
        position.profit_loss = profit_loss
        position.sell_commission = sell_commission
        position.commission = total_commission
        position.actual_risk_reward_ratio = actual_rrr
        position.updated_at = close_time

        await db.commit()
        await db.refresh(position)

        strategy = await _get_stock_strategy(db, current_user, position.strategy_id)
        start_date = position.open_time.date() if position.open_time else close_time.date()
        await recalculate_strategy_capital_history(db, current_user.id, strategy.id, start_date)

        pos_dict = position.__dict__.copy()
        pos_dict['risk_reward_ratio'] = position.theoretical_risk_reward_ratio
        pos_dict['theoretical_risk_reward_ratio'] = position.theoretical_risk_reward_ratio
        pos_dict['actual_risk_reward_ratio'] = actual_rrr

        return TradeResponse(**pos_dict)

    remaining_shares = position.shares - shares_to_close
    remaining_buy_commission = round(original_buy_commission - closed_buy_commission, 6)

    closed_trade = Trade(
        user_id=position.user_id,
        strategy_id=position.strategy_id,
        stock_code=position.stock_code,
        stock_name=position.stock_name,
        open_time=position.open_time,
        close_time=close_time,
        shares=shares_to_close,
        commission=total_commission,
        buy_commission=closed_buy_commission,
        sell_commission=sell_commission,
        buy_price=position.buy_price,
        sell_price=request.sell_price,
        stop_loss_price=position.stop_loss_price,
        take_profit_price=position.take_profit_price,
        stop_loss_alert=position.stop_loss_alert,
        take_profit_alert=position.take_profit_alert,
        holding_days=holding_days,
        order_result="止损",
        profit_loss=profit_loss,
        theoretical_risk_reward_ratio=position.theoretical_risk_reward_ratio,
        actual_risk_reward_ratio=actual_rrr,
        notes=position.notes or "",
        status="closed",
    )

    position.shares = remaining_shares
    position.buy_commission = remaining_buy_commission
    position.commission = remaining_buy_commission
    position.updated_at = close_time

    db.add(closed_trade)

    await db.commit()
    await db.refresh(closed_trade)
    
    strategy = await _get_stock_strategy(db, current_user, position.strategy_id)
    start_date = position.open_time.date() if position.open_time else close_time.date()
    await recalculate_strategy_capital_history(db, current_user.id, strategy.id, start_date)
    
    trade_dict = closed_trade.__dict__.copy()
    trade_dict['risk_reward_ratio'] = closed_trade.theoretical_risk_reward_ratio
    trade_dict['theoretical_risk_reward_ratio'] = closed_trade.theoretical_risk_reward_ratio
    trade_dict['actual_risk_reward_ratio'] = closed_trade.actual_risk_reward_ratio

    return TradeResponse(**trade_dict)
