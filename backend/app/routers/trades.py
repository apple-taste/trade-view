from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, distinct
from datetime import datetime, date, timedelta, timezone
import logging

logger = logging.getLogger(__name__)

from app.database import get_db, Trade, CapitalHistory
from app.middleware.auth import get_current_user
from app.models import TradeCreate, TradeUpdate, TradeResponse
from app.database import User
from app.routers.user import recalculate_capital_history
from app.services.commission_calculator import default_calculator

router = APIRouter()

@router.get(
    "",
    response_model=list[TradeResponse],
    summary="获取所有交易记录",
    description="""
    获取当前用户的所有交易记录（历史订单）。
    
    返回所有交易记录的列表，按开仓时间倒序排列。
    包括已平仓和未平仓的所有交易记录。
    **不包含已删除的记录**。
    """,
    responses={
        200: {"description": "成功返回所有交易记录列表"}
    }
)
async def get_all_trades(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Trade)
        .where(Trade.user_id == current_user.id, Trade.is_deleted == False)
        .order_by(Trade.open_time.desc())
    )
    trades = result.scalars().all()
    
    # 计算风险回报比并构建响应
    trade_responses = []
    for trade in trades:
        trade_dict = trade.__dict__.copy()
        # 计算风险回报比：(止盈价-买入价)/(买入价-止损价)
        if trade.buy_price and trade.stop_loss_price and trade.take_profit_price:
            risk = trade.buy_price - trade.stop_loss_price  # 止损距离（风险）
            reward = trade.take_profit_price - trade.buy_price  # 止盈距离（回报）
            if risk > 0:
                trade_dict['risk_reward_ratio'] = round(reward / risk, 2)
            else:
                trade_dict['risk_reward_ratio'] = None
        else:
            trade_dict['risk_reward_ratio'] = None
        trade_responses.append(TradeResponse(**trade_dict))
    
    return trade_responses

@router.get(
    "/date/{trade_date}",
    response_model=list[TradeResponse],
    summary="按日期获取交易记录",
    description="""
    获取指定日期的所有交易记录。
    
    - **trade_date**: 日期，格式：YYYY-MM-DD（例如：2024-01-11）
    
    返回该日期所有交易记录的列表，按开仓时间倒序排列。
    """,
    responses={
        200: {"description": "成功返回交易记录列表"},
        400: {"description": "日期格式错误"}
    }
)
async def get_trades_by_date(
    trade_date: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        date_obj = datetime.strptime(trade_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD")
    
    # 使用日期范围查询，确保与日历标记逻辑一致
    # 用户选择的是北京时间日期，需要查询该日期对应的UTC时间范围
    # 北京时间 00:00:00 = UTC时间 前一天的 16:00:00
    # 北京时间 23:59:59 = UTC时间 当天的 15:59:59
    # 所以查询范围：UTC时间从 (date_obj - 1天) 16:00:00 到 date_obj 16:00:00
    beijing_start = datetime.combine(date_obj, datetime.min.time())
    beijing_end = datetime.combine(date_obj, datetime.max.time()) + timedelta(days=1)
    
    # 转换为UTC时间范围（北京时间 - 8小时）
    start_datetime = beijing_start - timedelta(hours=8)
    end_datetime = beijing_end - timedelta(hours=8)
    
    result = await db.execute(
        select(Trade)
        .where(
            Trade.user_id == current_user.id,
            Trade.open_time >= start_datetime,
            Trade.open_time < end_datetime,
            Trade.is_deleted == False  # 排除已删除的记录
        )
        .order_by(Trade.open_time.desc())
    )
    trades = result.scalars().all()
    
    # 计算风险回报比并构建响应
    trade_responses = []
    for trade in trades:
        trade_dict = trade.__dict__.copy()
        # 计算风险回报比：(止盈价-买入价)/(买入价-止损价)
        if trade.buy_price and trade.stop_loss_price and trade.take_profit_price:
            risk = trade.buy_price - trade.stop_loss_price  # 止损距离（风险）
            reward = trade.take_profit_price - trade.buy_price  # 止盈距离（回报）
            if risk > 0:
                trade_dict['risk_reward_ratio'] = round(reward / risk, 2)
            else:
                trade_dict['risk_reward_ratio'] = None
        else:
            trade_dict['risk_reward_ratio'] = None
        trade_responses.append(TradeResponse(**trade_dict))
    
    return trade_responses

@router.post(
    "",
    response_model=TradeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建交易记录",
    description="""
    创建一条新的开仓交易记录。
    
    **必填字段**:
    - stock_code: 股票代码（如：600879）
    - shares: 买入股数
    - buy_price: 实际买入价格
    
    **可选字段**:
    - stock_name: 股票名称（可从代码中解析，如：600879-航空电子）
    - open_time: 开仓时间（默认当前时间）
    - commission: 手续费（默认0）
    - stop_loss_price: 止损价格
    - take_profit_price: 止盈价格
    - stop_loss_alert: 是否启用止损提醒
    - take_profit_alert: 是否启用止盈提醒
    - notes: 交易备注
    """,
    responses={
        201: {"description": "交易记录创建成功"},
        400: {"description": "必填字段缺失"}
    }
)
async def create_trade(
    trade_data: TradeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 处理open_time：如果有时区信息，转换为naive UTC时间
    if trade_data.open_time:
        open_time = trade_data.open_time
        # 如果datetime有时区信息，转换为UTC naive datetime
        if open_time.tzinfo is not None:
            # 转换为UTC时间（如果有其他时区）
            open_time = open_time.astimezone(timezone.utc).replace(tzinfo=None)
    else:
        open_time = datetime.utcnow()
    
    # 添加调试日志
    logger.info(f"📝 [创建交易] 用户 {current_user.username}, 股票 {trade_data.stock_code}")
    logger.info(f"   接收到的open_time: {trade_data.open_time}")
    logger.info(f"   处理后的open_time (UTC): {open_time}")
    logger.info(f"   UTC日期: {open_time.date()}")
    # 转换为北京时间用于日志
    beijing_time_for_log = open_time + timedelta(hours=8)
    logger.info(f"   北京时间: {beijing_time_for_log}")
    logger.info(f"   北京时间日期: {beijing_time_for_log.date()}")
    
    # 如果用户没有提供买入手续费，自动计算
    buy_commission = trade_data.buy_commission
    if buy_commission is None or buy_commission == 0:
        buy_commission = default_calculator.calculate_buy_commission(
            trade_data.buy_price,
            trade_data.shares
        )
    
    # commission字段保持兼容性（开仓时等于买入手续费）
    commission = trade_data.commission if trade_data.commission else buy_commission
    
    # 计算理论风险回报比（开仓时根据计划的止盈止损价格）
    theoretical_rrr = None
    if trade_data.buy_price and trade_data.stop_loss_price and trade_data.take_profit_price:
        risk = trade_data.buy_price - trade_data.stop_loss_price
        reward = trade_data.take_profit_price - trade_data.buy_price
        if risk > 0:
            theoretical_rrr = round(reward / risk, 2)
    
    new_trade = Trade(
        user_id=current_user.id,
        stock_code=trade_data.stock_code,
        stock_name=trade_data.stock_name,
        open_time=open_time,
        shares=trade_data.shares,
        commission=commission,
        buy_commission=buy_commission,
        sell_commission=0,  # 开仓时卖出手续费为0
        buy_price=trade_data.buy_price,
        stop_loss_price=trade_data.stop_loss_price,
        take_profit_price=trade_data.take_profit_price,
        stop_loss_alert=trade_data.stop_loss_alert or False,
        take_profit_alert=trade_data.take_profit_alert or False,
        theoretical_risk_reward_ratio=theoretical_rrr,  # 理论风险回报比
        actual_risk_reward_ratio=None,  # 开仓时无实际比率
        notes=trade_data.notes or "",
        status="open"
    )
    
    db.add(new_trade)
    
    await db.commit()
    await db.refresh(new_trade)
    
    # 重新计算资金曲线（从初始资金日期开始）
    # 这样确保资金曲线的一致性，避免直接更新导致的错误
    result = await db.execute(
        select(CapitalHistory)
        .where(CapitalHistory.user_id == current_user.id)
        .order_by(CapitalHistory.date.asc())
        .limit(1)
    )
    initial_capital_record = result.scalar_one_or_none()
    
    if initial_capital_record:
        # 使用初始资金设置的日期作为起点重新计算
        await recalculate_capital_history(db, current_user.id, initial_capital_record.date)
    else:
        # 如果没有初始资金记录，使用交易的开仓日期
        await recalculate_capital_history(db, current_user.id, open_time.date())
    
    # 准备返回数据（保持兼容性）
    trade_dict = new_trade.__dict__.copy()
    trade_dict['risk_reward_ratio'] = theoretical_rrr  # 兼容旧版
    trade_dict['theoretical_risk_reward_ratio'] = theoretical_rrr
    trade_dict['actual_risk_reward_ratio'] = None
    
    return TradeResponse(**trade_dict)

async def update_capital_from_trade(db: AsyncSession, user_id: int, amount_change: float, trade_date: date):
    """
    根据交易更新资金历史
    amount_change: 资金变化量（正数为增加，负数为减少）
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
        new_capital = latest_capital.capital + amount_change
    else:
        # 如果没有历史记录，使用默认值10万
        new_capital = 100000.0 + amount_change
    
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

@router.put("/{trade_id}", response_model=TradeResponse)
async def update_trade(
    trade_id: int,
    trade_data: TradeUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Trade).where(
            Trade.id == trade_id,
            Trade.user_id == current_user.id,
            Trade.is_deleted == False  # 只能更新未删除的记录
        )
    )
    trade = result.scalar_one_or_none()
    
    if not trade:
        raise HTTPException(status_code=404, detail="交易记录不存在或已被删除")
    
    # 记录旧的手续费、买入价格和股数，用于判断是否需要重新计算资金曲线
    old_commission = trade.commission
    old_buy_price = trade.buy_price
    old_shares = trade.shares
    
    # 更新交易记录字段
    update_data = trade_data.model_dump(exclude_unset=True)
    
    # 如果用户更新了买入价格或股数，且没有提供手续费，自动重新计算手续费
    if 'commission' not in update_data or update_data['commission'] is None:
        # 使用更新后的价格和股数，如果没有更新则使用原来的值
        buy_price = update_data.get('buy_price', trade.buy_price)
        shares = update_data.get('shares', trade.shares)
        
        # 如果买入价格或股数有变化，重新计算手续费
        if 'buy_price' in update_data or 'shares' in update_data:
            update_data['commission'] = default_calculator.calculate_buy_commission(
                buy_price,
                shares
            )
    
    for field, value in update_data.items():
        if value is not None:
            setattr(trade, field, value)
    
    trade.updated_at = datetime.utcnow()
    
    # 检查手续费、买入价格或股数是否有变化，如果有变化需要重新计算资金曲线
    commission_changed = trade.commission != old_commission
    price_changed = trade.buy_price != old_buy_price
    shares_changed = trade.shares != old_shares
    
    await db.commit()
    await db.refresh(trade)
    
    # 如果手续费、买入价格或股数有变化，需要重新计算资金曲线
    if commission_changed or price_changed or shares_changed:
        # 找到用户设置的初始资金日期（最早的 CapitalHistory 记录）
        result = await db.execute(
            select(CapitalHistory)
            .where(CapitalHistory.user_id == current_user.id)
            .order_by(CapitalHistory.date.asc())
            .limit(1)
        )
        initial_capital_record = result.scalar_one_or_none()
        
        if initial_capital_record:
            # 使用初始资金设置的日期作为起点重新计算
            await recalculate_capital_history(db, current_user.id, initial_capital_record.date)
    
    # 计算风险回报比
    trade_dict = trade.__dict__.copy()
    if trade.buy_price and trade.stop_loss_price and trade.take_profit_price:
        risk = trade.buy_price - trade.stop_loss_price
        reward = trade.take_profit_price - trade.buy_price
        if risk > 0:
            trade_dict['risk_reward_ratio'] = round(reward / risk, 2)
        else:
            trade_dict['risk_reward_ratio'] = None
    else:
        trade_dict['risk_reward_ratio'] = None
    
    return TradeResponse(**trade_dict)

@router.delete("/clear-all")
async def clear_all_trades(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    一键清空所有交易记录（软删除）并重算资金曲线。
    - 将当前用户所有 Trade.is_deleted=False 的交易标记为 True
    - 然后从用户初始入金日期开始重算资金曲线
    """
    # 优先使用 users.initial_capital_date 作为重算起点
    start_date = getattr(current_user, "initial_capital_date", None)
    if not start_date:
        result = await db.execute(
            select(CapitalHistory)
            .where(CapitalHistory.user_id == current_user.id)
            .order_by(CapitalHistory.date.asc())
            .limit(1)
        )
        initial_capital_record = result.scalar_one_or_none()
        start_date = initial_capital_record.date if initial_capital_record else date.today()

    result = await db.execute(
        select(Trade).where(
            Trade.user_id == current_user.id,
            Trade.is_deleted == False
        )
    )
    trades = result.scalars().all()
    for t in trades:
        t.is_deleted = True
        t.updated_at = datetime.utcnow()

    await db.commit()

    # 无有效交易时，recalculate_capital_history 会强制恢复为初始入金
    await recalculate_capital_history(db, current_user.id, start_date)

    return {"message": "清空成功，资金曲线已重新计算", "deleted_count": len(trades)}

@router.delete("/{trade_id}")
async def delete_trade(
    trade_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    软删除交易记录。
    将 is_deleted 设置为 True，而不是真正删除记录。
    已删除的记录不会出现在持仓面板和统计中。
    
    删除交易后，会重新计算资金曲线（从用户设置的初始资金日期开始）。
    """
    result = await db.execute(
        select(Trade).where(
            Trade.id == trade_id,
            Trade.user_id == current_user.id,
            Trade.is_deleted == False  # 只能删除未删除的记录
        )
    )
    trade = result.scalar_one_or_none()
    
    if not trade:
        raise HTTPException(status_code=404, detail="交易记录不存在或已被删除")
    
    # 获取交易的开仓日期（用于确定重新计算的起点）
    trade_open_date = trade.open_time.date() if trade.open_time else date.today()
    
    # 找到用户设置的初始资金日期（优先 users.initial_capital_date）
    start_date = getattr(current_user, "initial_capital_date", None)
    if not start_date:
        result = await db.execute(
            select(CapitalHistory)
            .where(CapitalHistory.user_id == current_user.id)
            .order_by(CapitalHistory.date.asc())
            .limit(1)
        )
        initial_capital_record = result.scalar_one_or_none()
        start_date = initial_capital_record.date if initial_capital_record else trade_open_date
    
    # 软删除：设置 is_deleted = True
    trade.is_deleted = True
    trade.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(trade)
    
    # 重新计算资金曲线（从初始资金日期开始）
    # 因为交易已被标记为删除，recalculate_capital_history 会自动排除它
    await recalculate_capital_history(db, current_user.id, start_date)
    
    return {"message": "删除成功，资金曲线已重新计算"}

@router.get(
    "/dates",
    response_model=list[str],
    summary="获取有交易记录的日期列表",
    description="""
    获取当前用户所有有交易记录的日期列表。
    
    返回格式：["2024-01-11", "2024-01-15", ...]
    用于在日历上标记有交易的日期。
    """,
    responses={
        200: {"description": "成功返回日期列表"}
    }
)
async def get_trade_dates(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        # 获取所有交易记录，然后提取日期（转换为北京时间后提取日期）
        # 确保用户在某个日期开仓，日历就在对应日期做标记
        result = await db.execute(
            select(Trade.open_time)
            .where(
                Trade.user_id == current_user.id,
                Trade.is_deleted == False  # 排除已删除的记录
            )
            .order_by(Trade.open_time.asc())
        )
        trade_times = result.scalars().all()
        
        # 提取唯一的日期（转换为北京时间后提取日期）
        # 北京时间 = UTC时间 + 8小时
        date_set = set()
        for trade_time in trade_times:
            if trade_time:
                # 将UTC时间转换为北京时间（+8小时），然后提取日期
                beijing_time = trade_time + timedelta(hours=8)
                date_set.add(beijing_time.date())
        
        # 转换为字符串格式 YYYY-MM-DD，并排序
        date_list = sorted([d.strftime("%Y-%m-%d") for d in date_set])
        return date_list
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"获取交易日期失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取交易日期失败: {str(e)}")
