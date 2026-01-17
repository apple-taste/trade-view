from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, distinct
from datetime import datetime, date, timedelta, timezone
import asyncio
import logging

logger = logging.getLogger(__name__)

from app.database import get_db, Trade, CapitalHistory, AsyncSessionLocal
from app.middleware.auth import get_current_user, billing_enabled, user_has_active_subscription
from app.models import TradeCreate, TradeUpdate, TradeResponse, PaginatedTradeResponse
from app.database import User
from app.routers.user import recalculate_capital_history, recalculate_strategy_capital_history, _get_stock_strategy
from app.services.commission_calculator import default_calculator
from app.services.price_monitor import price_monitor

router = APIRouter()

@router.get(
    "",
    response_model=PaginatedTradeResponse,
    summary="获取所有交易记录（分页）",
    description="""
    获取当前用户的所有交易记录（历史订单）。
    
    支持分页查询，默认返回第1页，每页50条。
    返回所有交易记录的列表，按开仓时间倒序排列。
    包括已平仓和未平仓的所有交易记录。
    **不包含已删除的记录**。
    """,
    responses={
        200: {"description": "成功返回分页交易记录列表"}
    }
)
async def get_all_trades(
    page: int = 1,
    page_size: int = 50,
    strategy_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    strategy = await _get_stock_strategy(db, current_user, strategy_id)
    # 计算总数
    count_result = await db.execute(
        select(func.count())
        .select_from(Trade)
        .where(
            Trade.user_id == current_user.id,
            Trade.strategy_id == strategy.id,
            Trade.is_deleted == False,
        )
    )
    total = count_result.scalar()
    
    # 计算偏移量
    offset = (page - 1) * page_size
    
    # 查询数据
    result = await db.execute(
        select(Trade)
        .where(
            Trade.user_id == current_user.id,
            Trade.strategy_id == strategy.id,
            Trade.is_deleted == False,
        )
        .order_by(Trade.open_time.desc())
        .offset(offset)
        .limit(page_size)
    )
    trades = result.scalars().all()
    
    # 收集需要获取名称的股票代码（批量处理，避免重复API调用）
    stock_codes_to_fetch = {}
    for trade in trades:
        if (not trade.stock_name or trade.stock_name.strip() == "") and trade.stock_code:
            if trade.stock_code not in stock_codes_to_fetch:
                stock_codes_to_fetch[trade.stock_code] = []
            stock_codes_to_fetch[trade.stock_code].append(trade)
    
    # 批量获取股票名称
    for stock_code, trades_list in stock_codes_to_fetch.items():
        fetched_name = await price_monitor.fetch_stock_name(stock_code)
        if fetched_name:
            for trade in trades_list:
                trade.stock_name = fetched_name
            logger.info(f"✅ 自动更新股票 {stock_code} 名称为: {fetched_name}")
    
    # 如果有更新，提交到数据库
    if stock_codes_to_fetch:
        await db.commit()
    
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
    
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
    
    return {
        "items": trade_responses,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }

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
    strategy_id: int | None = None,
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
    
    strategy = await _get_stock_strategy(db, current_user, strategy_id)
    result = await db.execute(
        select(Trade)
        .where(
            Trade.user_id == current_user.id,
            Trade.strategy_id == strategy.id,
            Trade.open_time >= start_datetime,
            Trade.open_time < end_datetime,
            Trade.is_deleted == False  # 排除已删除的记录
        )
        .order_by(Trade.open_time.desc())
    )
    trades = result.scalars().all()
    
    # 收集需要获取名称的股票代码（批量处理，避免重复API调用）
    stock_codes_to_fetch = {}
    for trade in trades:
        if (not trade.stock_name or trade.stock_name.strip() == "") and trade.stock_code:
            if trade.stock_code not in stock_codes_to_fetch:
                stock_codes_to_fetch[trade.stock_code] = []
            stock_codes_to_fetch[trade.stock_code].append(trade)
    
    # 批量获取股票名称
    for stock_code, trades_list in stock_codes_to_fetch.items():
        fetched_name = await price_monitor.fetch_stock_name(stock_code)
        if fetched_name:
            for trade in trades_list:
                trade.stock_name = fetched_name
            logger.info(f"✅ 自动更新股票 {stock_code} 名称为: {fetched_name}")
    
    # 如果有更新，提交到数据库
    if stock_codes_to_fetch:
        await db.commit()
    
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
    async def _recalculate_strategy_capital_history_async(user_id: int, strategy_id: int, start_date: date):
        try:
            async with AsyncSessionLocal() as session:
                await recalculate_strategy_capital_history(session, user_id, strategy_id, start_date)
        except Exception:
            logger.exception("recalculate_strategy_capital_history failed")

    if billing_enabled() and not user_has_active_subscription(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "BILLING_REQUIRED", "message": "非Pro会员无法新增交易记录，请先开通Pro会员"},
        )

    stock_code = (trade_data.stock_code or "").strip()
    stock_name = trade_data.stock_name
    if (not stock_name or stock_name.strip() == "") and stock_code:
        if "-" in stock_code:
            left, right = stock_code.split("-", 1)
            if right.strip():
                stock_name = right.strip()
            stock_code = left.strip()
        elif " " in stock_code:
            left, right = stock_code.split(" ", 1)
            if right.strip():
                stock_name = right.strip()
            stock_code = left.strip()

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
    logger.info(f"📝 [创建交易] 用户 {current_user.username}, 股票 {stock_code}, 名称: {stock_name}")
    logger.info(f"   接收到的open_time: {trade_data.open_time}")
    logger.info(f"   处理后的open_time (UTC): {open_time}")
    logger.info(f"   UTC日期: {open_time.date()}")
    # 转换为北京时间用于日志
    beijing_time_for_log = open_time + timedelta(hours=8)
    logger.info(f"   北京时间: {beijing_time_for_log}")
    logger.info(f"   北京时间日期: {beijing_time_for_log.date()}")
    
    # 处理手数：如果提供了单笔风险和止损价格，自动计算手数
    shares = trade_data.shares
    if shares is None or shares == 0:
        # 如果用户没有提供手数，尝试根据单笔风险计算
        if trade_data.risk_per_trade and trade_data.risk_per_trade > 0:
            if trade_data.stop_loss_price and trade_data.stop_loss_price < trade_data.buy_price:
                # 计算每股风险
                risk_per_share = trade_data.buy_price - trade_data.stop_loss_price
                if risk_per_share > 0:
                    # 计算手数：单笔风险 / 每股风险，向上取整
                    calculated_shares = trade_data.risk_per_trade / risk_per_share
                    shares = int(calculated_shares) + (1 if calculated_shares % 1 > 0 else 0)  # 向上取整
                    logger.info(f"   💰 [单笔风险] 单笔风险: {trade_data.risk_per_trade}, 每股风险: {risk_per_share:.2f}, 计算手数: {shares}")
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="止损价格必须小于买入价格"
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="使用单笔风险计算手数时，必须提供止损价格且止损价格必须小于买入价格"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="必须提供手数(shares)或单笔风险(risk_per_trade)"
            )
    
    # 如果用户没有提供买入手续费，自动计算
    buy_commission = trade_data.buy_commission
    if buy_commission is None or buy_commission == 0:
        buy_commission = default_calculator.calculate_buy_commission(
            trade_data.buy_price,
            shares
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
    
    strategy = await _get_stock_strategy(db, current_user, trade_data.strategy_id)
    new_trade = Trade(
        user_id=current_user.id,
        strategy_id=strategy.id,
        stock_code=stock_code,
        stock_name=stock_name,
        open_time=open_time,
        shares=shares,
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
    asyncio.create_task(_recalculate_strategy_capital_history_async(current_user.id, strategy.id, open_time.date()))
    
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
    try:
        logger.info(f"📝 [更新交易] 开始更新交易 ID: {trade_id}, 用户: {current_user.username}")
        
        result = await db.execute(
            select(Trade).where(
                Trade.id == trade_id,
                Trade.user_id == current_user.id,
                Trade.is_deleted == False  # 只能更新未删除的记录
            )
        )
        trade = result.scalar_one_or_none()
        
        if not trade:
            logger.warning(f"⚠️ [更新交易] 交易记录不存在或已被删除: ID={trade_id}, 用户={current_user.username}")
            raise HTTPException(status_code=404, detail="交易记录不存在或已被删除")
        
        # 记录旧的值，用于判断是否需要重新计算资金曲线
        old_commission = trade.commission
        old_buy_price = trade.buy_price
        old_shares = trade.shares
        old_sell_price = trade.sell_price
        old_sell_commission = trade.sell_commission
        old_profit_loss = trade.profit_loss
        old_close_time = trade.close_time
        old_strategy_id = trade.strategy_id
        
        # 更新交易记录字段
        update_data = trade_data.model_dump(exclude_unset=True)
        logger.info(f"📝 [更新交易] 接收到的更新数据: {update_data}")

        if "strategy_id" in update_data and update_data["strategy_id"] is not None:
            strategy = await _get_stock_strategy(db, current_user, int(update_data["strategy_id"]))
            update_data["strategy_id"] = strategy.id
        
        # 处理open_time（如果提供了）- 确保是naive datetime
        if 'open_time' in update_data and update_data['open_time']:
            from datetime import datetime as dt, timezone
            if isinstance(update_data['open_time'], str):
                try:
                    # 处理ISO格式字符串，支持带Z或不带时区
                    open_time_str = update_data['open_time'].replace('Z', '+00:00')
                    if '+' not in open_time_str and open_time_str.count(':') >= 2:
                        # 如果没有时区信息，假设是UTC
                        open_time_str += '+00:00'
                    update_data['open_time'] = dt.fromisoformat(open_time_str)
                    # 转换为UTC naive datetime
                    if update_data['open_time'].tzinfo:
                        update_data['open_time'] = update_data['open_time'].astimezone(timezone.utc).replace(tzinfo=None)
                    logger.info(f"✅ [更新交易] open_time 解析成功: {update_data['open_time']}")
                except Exception as e:
                    logger.error(f"❌ [更新交易] 解析open_time失败: {e}, 原始值: {update_data['open_time']}")
                    raise HTTPException(status_code=400, detail=f"开仓时间格式错误: {str(e)}")
            elif isinstance(update_data['open_time'], dt):
                # 如果已经是datetime对象，确保是naive
                if update_data['open_time'].tzinfo:
                    update_data['open_time'] = update_data['open_time'].astimezone(timezone.utc).replace(tzinfo=None)
                    logger.info(f"✅ [更新交易] open_time 时区已移除: {update_data['open_time']}")
        
        # 处理close_time（如果提供了）- 确保是naive datetime
        if 'close_time' in update_data:
            if update_data['close_time'] is None or update_data['close_time'] == '':
                # 如果明确设置为 None 或空字符串，则清空 close_time
                update_data['close_time'] = None
            elif isinstance(update_data['close_time'], str):
                # 如果是字符串，转换为datetime
                from datetime import datetime as dt, timezone
                try:
                    # 处理ISO格式字符串，支持带Z或不带时区
                    close_time_str = update_data['close_time'].replace('Z', '+00:00')
                    if '+' not in close_time_str and close_time_str.count(':') >= 2:
                        # 如果没有时区信息，假设是UTC
                        close_time_str += '+00:00'
                    update_data['close_time'] = dt.fromisoformat(close_time_str)
                    # 转换为UTC naive datetime
                    if update_data['close_time'].tzinfo:
                        update_data['close_time'] = update_data['close_time'].astimezone(timezone.utc).replace(tzinfo=None)
                    logger.info(f"✅ [更新交易] close_time 解析成功: {update_data['close_time']}")
                except Exception as e:
                    logger.error(f"❌ [更新交易] 解析close_time失败: {e}, 原始值: {update_data['close_time']}")
                    raise HTTPException(status_code=400, detail=f"离场时间格式错误: {str(e)}")
            elif isinstance(update_data['close_time'], dt):
                # 如果已经是datetime对象，确保是naive
                if update_data['close_time'].tzinfo:
                    from datetime import timezone
                    update_data['close_time'] = update_data['close_time'].astimezone(timezone.utc).replace(tzinfo=None)
                    logger.info(f"✅ [更新交易] close_time 时区已移除: {update_data['close_time']}")
        
        # 如果用户更新了买入价格或股数，且没有提供手续费，自动重新计算手续费
        if 'commission' not in update_data or update_data['commission'] is None:
            # 使用更新后的价格和股数，如果没有更新则使用原来的值
            buy_price = update_data.get('buy_price', trade.buy_price)
            shares = update_data.get('shares', trade.shares)
            
            # 如果买入价格或股数有变化，重新计算买入手续费
            if 'buy_price' in update_data or 'shares' in update_data:
                buy_commission = default_calculator.calculate_buy_commission(buy_price, shares)
                if 'buy_commission' not in update_data:
                    update_data['buy_commission'] = buy_commission
        
        # 如果用户更新了离场价格，重新计算盈亏和卖出手续费
        if 'sell_price' in update_data and update_data['sell_price'] is not None:
            sell_price = update_data['sell_price']
            shares = update_data.get('shares', trade.shares)
            buy_price = update_data.get('buy_price', trade.buy_price)
            
            # 计算卖出手续费（如果没有提供）
            if 'sell_commission' not in update_data or update_data['sell_commission'] is None:
                sell_commission = default_calculator.calculate_sell_commission(
                    sell_price,
                    shares,
                    trade.stock_code
                )
                update_data['sell_commission'] = sell_commission
            
            # 计算盈亏：(卖出价 - 买入价) * 手数 - 总手续费
            buy_commission = update_data.get('buy_commission', trade.buy_commission) or 0
            sell_commission = update_data.get('sell_commission', trade.sell_commission) or 0
            total_commission = buy_commission + sell_commission
            
            profit_loss = (sell_price - buy_price) * shares - total_commission
            update_data['profit_loss'] = round(profit_loss, 2)
            update_data['commission'] = total_commission  # 更新总手续费
            
            # 计算实际风险回报比
            if trade.stop_loss_price:
                risk = buy_price - trade.stop_loss_price
                actual_reward = sell_price - buy_price
                if risk > 0:
                    update_data['actual_risk_reward_ratio'] = round(actual_reward / risk, 2)
            
            # 如果交易已平仓，更新状态
            if 'status' not in update_data:
                update_data['status'] = 'closed'
            
            logger.info(f"📝 [更新交易] 修改离场价格: {trade.stock_code}, 旧价格: {old_sell_price}, 新价格: {sell_price}, 盈亏: {profit_loss:.2f}")
        
        for field, value in update_data.items():
            if value is not None:
                setattr(trade, field, value)
        
        trade.updated_at = datetime.utcnow()
        
        # 检查是否有影响资金曲线的字段变化
        commission_changed = trade.commission != old_commission
        price_changed = trade.buy_price != old_buy_price
        shares_changed = trade.shares != old_shares
        sell_price_changed = trade.sell_price != old_sell_price
        sell_commission_changed = trade.sell_commission != old_sell_commission
        close_time_changed = trade.close_time != old_close_time
        
        await db.commit()
        await db.refresh(trade)
        
        strategy_changed = trade.strategy_id != old_strategy_id
        if (
            commission_changed
            or price_changed
            or shares_changed
            or sell_price_changed
            or sell_commission_changed
            or close_time_changed
            or strategy_changed
        ):
            strategy_ids: set[int] = set()
            if old_strategy_id is not None:
                strategy_ids.add(int(old_strategy_id))
            if trade.strategy_id is not None:
                strategy_ids.add(int(trade.strategy_id))

            for sid in strategy_ids:
                await recalculate_strategy_capital_history(db, current_user.id, sid, trade.open_time.date())
        
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
        
        logger.info(f"✅ [更新交易] 交易更新成功: ID={trade_id}, 股票={trade.stock_code}")
        return TradeResponse(**trade_dict)
    
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        logger.error(f"❌ [更新交易] 更新失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新交易失败: {str(e)}")

@router.delete("/clear-all")
async def clear_all_trades(
    strategy_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    一键清空所有交易记录（软删除）并重算资金曲线。
    - 将当前用户所有 Trade.is_deleted=False 的交易标记为 True
    - 然后从用户初始入金日期开始重算资金曲线
    """
    if strategy_id is not None:
        strategy = await _get_stock_strategy(db, current_user, strategy_id)
        result = await db.execute(
            select(Trade).where(
                Trade.user_id == current_user.id,
                Trade.strategy_id == strategy.id,
                Trade.is_deleted == False,
            )
        )
        trades = result.scalars().all()
        for t in trades:
            t.is_deleted = True
            t.updated_at = datetime.utcnow()

        await db.commit()
        await recalculate_strategy_capital_history(db, current_user.id, strategy.id, date.today())
        return {"message": "清空成功，资金曲线已重新计算", "deleted_count": len(trades)}

    result = await db.execute(
        select(Trade).where(Trade.user_id == current_user.id, Trade.is_deleted == False)
    )
    trades = result.scalars().all()
    for t in trades:
        t.is_deleted = True
        t.updated_at = datetime.utcnow()

    await db.commit()

    start_date = getattr(current_user, "initial_capital_date", None)
    if start_date is None:
        start_date = date.today()
    await recalculate_capital_history(db, current_user.id, start_date)

    strat_result = await db.execute(
        select(func.distinct(Trade.strategy_id)).where(
            Trade.user_id == current_user.id,
            Trade.strategy_id.isnot(None),
        )
    )
    strategy_ids = [row[0] for row in strat_result.fetchall() if row[0] is not None]
    for sid in strategy_ids:
        await recalculate_strategy_capital_history(db, current_user.id, int(sid), date.today())

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
    
    # 软删除：设置 is_deleted = True
    trade.is_deleted = True
    trade.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(trade)
    
    strategy = await _get_stock_strategy(db, current_user, trade.strategy_id)
    await recalculate_strategy_capital_history(db, current_user.id, strategy.id, date.today())
    
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
    strategy_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        strategy = await _get_stock_strategy(db, current_user, strategy_id)
        # 获取所有交易记录，然后提取日期（转换为北京时间后提取日期）
        # 确保用户在某个日期开仓，日历就在对应日期做标记
        result = await db.execute(
            select(Trade.open_time)
            .where(
                Trade.user_id == current_user.id,
                Trade.strategy_id == strategy.id,
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

@router.get(
    "/stock-codes",
    response_model=list[dict],
    summary="获取所有股票代码列表",
    description="""
    获取当前用户所有交易记录中的唯一股票代码列表（包含股票名称）。
    
    返回格式：[{"code": "600879", "name": "航空电子"}, {"code": "002426", "name": "胜利精密"}, ...]
    用于在历史订单面板中按股票代码筛选。
    """,
    responses={
        200: {"description": "成功返回股票代码列表"}
    }
)
async def get_stock_codes(
    strategy_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        strategy = await _get_stock_strategy(db, current_user, strategy_id)
        # 获取所有交易记录，然后提取唯一的股票代码和名称
        result = await db.execute(
            select(Trade.stock_code, Trade.stock_name)
            .where(
                Trade.user_id == current_user.id,
                Trade.strategy_id == strategy.id,
                Trade.is_deleted == False,
                Trade.stock_code.isnot(None)
            )
            .order_by(Trade.stock_code.asc())
        )
        stock_data = result.all()
        
        # 构建返回数据：去重并保留股票名称（取第一个非空的名称）
        stock_dict = {}
        for code, name in stock_data:
            if code:
                if code not in stock_dict:
                    stock_dict[code] = name or ""
                elif not stock_dict[code] and name:
                    # 如果之前没有名称，现在有名称了，更新它
                    stock_dict[code] = name
        
        # 转换为列表格式
        stock_list = [{"code": code, "name": name} for code, name in sorted(stock_dict.items())]
        return stock_list
    except Exception as e:
        logger.error(f"获取股票代码列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取股票代码列表失败: {str(e)}")

@router.get(
    "/stock/{stock_code}",
    response_model=dict,
    summary="按股票代码获取交易记录和统计信息",
    description="""
    获取指定股票代码的所有交易记录和统计信息。
    
    - **stock_code**: 股票代码（如：600879）
    
    返回格式：
    {
        "trades": [...],  // 该股票的所有交易记录
        "statistics": {
            "total_profit_loss": 1234.56,  // 合计盈亏
            "average_theoretical_risk_reward_ratio": 2.5,  // 平均理论风险回报比
            "trade_count": 5  // 交易次数
        }
    }
    """,
    responses={
        200: {"description": "成功返回交易记录和统计信息"},
        404: {"description": "未找到该股票的交易记录"}
    }
)
async def get_trades_by_stock_code(
    stock_code: str,
    strategy_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        strategy = await _get_stock_strategy(db, current_user, strategy_id)
        # 获取该股票的所有交易记录
        result = await db.execute(
            select(Trade)
            .where(
                Trade.user_id == current_user.id,
                Trade.strategy_id == strategy.id,
                Trade.stock_code == stock_code,
                Trade.is_deleted == False
            )
            .order_by(Trade.open_time.desc())
        )
        trades = result.scalars().all()
        
        if not trades:
            raise HTTPException(status_code=404, detail=f"未找到股票代码 {stock_code} 的交易记录")
        
        # 计算风险回报比并构建响应
        trade_responses = []
        total_profit_loss = 0.0
        theoretical_risk_reward_ratios = []
        
        for trade in trades:
            trade_dict = trade.__dict__.copy()
            
            # 计算风险回报比
            if trade.buy_price and trade.stop_loss_price and trade.take_profit_price:
                risk = trade.buy_price - trade.stop_loss_price
                reward = trade.take_profit_price - trade.buy_price
                if risk > 0:
                    ratio = round(reward / risk, 2)
                    trade_dict['risk_reward_ratio'] = ratio
                    theoretical_risk_reward_ratios.append(ratio)
                else:
                    trade_dict['risk_reward_ratio'] = None
            else:
                trade_dict['risk_reward_ratio'] = None
            
            # 累计盈亏（如果有profit_loss字段）
            if hasattr(trade, 'profit_loss') and trade.profit_loss is not None:
                total_profit_loss += trade.profit_loss
            elif trade.sell_price and trade.buy_price:
                # 手动计算盈亏：(卖出价 - 买入价) * 手数 - 手续费
                profit = (trade.sell_price - trade.buy_price) * trade.shares
                commission = trade.commission or 0
                total_profit_loss += (profit - commission)
            
            trade_responses.append(TradeResponse(**trade_dict))
        
        # 计算平均理论风险回报比
        avg_theoretical_risk_reward_ratio = None
        if theoretical_risk_reward_ratios:
            avg_theoretical_risk_reward_ratio = round(
                sum(theoretical_risk_reward_ratios) / len(theoretical_risk_reward_ratios),
                2
            )
        
        return {
            "trades": trade_responses,
            "statistics": {
                "total_profit_loss": round(total_profit_loss, 2),
                "average_theoretical_risk_reward_ratio": avg_theoretical_risk_reward_ratio,
                "trade_count": len(trades)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取股票 {stock_code} 的交易记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取交易记录失败: {str(e)}")
