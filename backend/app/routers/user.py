from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from datetime import date, datetime

from app.database import get_db, User, CapitalHistory, Trade
from app.middleware.auth import get_current_user
from app.models import CapitalUpdate, CapitalHistoryItem, UserResponse
from app.services.commission_calculator import default_calculator
from app.services.email_service import default_email_service

router = APIRouter()

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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户的资金历史记录，用于绘制资金曲线。
    
    重要：当用户更新资金后，会删除该日期之后的所有记录并重新计算。
    因此，返回的数据应该从最早的记录开始（即用户设置的初始资金日期）。
    """
    query = select(CapitalHistory).where(CapitalHistory.user_id == current_user.id)
    
    if start_date:
        query = query.where(CapitalHistory.date >= start_date)
    if end_date:
        query = query.where(CapitalHistory.date <= end_date)
    
    query = query.order_by(CapitalHistory.date.asc())
    
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
    
    # 删除该日期之后的所有资金历史记录
    result = await db.execute(
        select(CapitalHistory).where(
            CapitalHistory.user_id == current_user.id,
            CapitalHistory.date >= update_date
        )
    )
    old_records = result.scalars().all()
    for record in old_records:
        await db.delete(record)
    
    # 删除该日期之前的所有资金历史记录（策略回测起点，之前的记录不应该存在）
    result = await db.execute(
        select(CapitalHistory).where(
            CapitalHistory.user_id == current_user.id,
            CapitalHistory.date < update_date
        )
    )
    old_before_records = result.scalars().all()
    for record in old_before_records:
        await db.delete(record)
    
    # 同步更新用户“初始入金锚点”（用于清空交易恢复初始资金 & 重算起点）
    current_user.initial_capital = capital_data.capital
    current_user.initial_capital_date = update_date

    # 检查是否已存在该日期的记录
    result = await db.execute(
        select(CapitalHistory).where(
            CapitalHistory.user_id == current_user.id,
            CapitalHistory.date == update_date
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        existing.capital = capital_data.capital
        existing.available_funds = capital_data.capital  # 初始资金全部为可用资金
        existing.position_value = 0.0  # 初始持仓市值为0
    else:
        new_history = CapitalHistory(
            user_id=current_user.id,
            date=update_date,
            capital=capital_data.capital,
            available_funds=capital_data.capital,  # 初始资金全部为可用资金
            position_value=0.0  # 初始持仓市值为0
        )
        db.add(new_history)
    
    await db.commit()
    
    # 重新计算资金曲线（基于交易记录）
    await recalculate_capital_history(db, current_user.id, update_date)
    
    return {"message": "初始资金设置成功，资金曲线已重新计算"}

async def get_current_total_assets(db: AsyncSession, user_id: int):
    """
    计算当前实时总资产（同花顺模式）
    
    总资产 = 可用资金 + 实时持仓市值
    
    注意：这里使用的是持仓股票的最新市场价格（current_price），
    而历史资金曲线使用的是买入价（持仓成本）。
    """
    # 获取最新的可用资金
    result = await db.execute(
        select(CapitalHistory)
        .where(CapitalHistory.user_id == user_id)
        .order_by(CapitalHistory.date.desc())
        .limit(1)
    )
    latest_record = result.scalar_one_or_none()
    
    if latest_record and latest_record.available_funds is not None:
        available_funds = latest_record.available_funds
    elif latest_record:
        available_funds = latest_record.capital
    else:
        available_funds = 100000.0
    
    # 查询所有当前持仓（status='open'）
    result = await db.execute(
        select(Trade)
        .where(
            Trade.user_id == user_id,
            Trade.status == "open",
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 使用实时计算函数获取当前总资产
    assets_info = await get_current_total_assets(db, current_user.id)
    
    return {
        "capital": assets_info["total_assets"],  # 总资产（兼容旧接口）
        "total_assets": assets_info["total_assets"],
        "available_funds": assets_info["available_funds"],
        "position_value": assets_info["position_value"]
    }

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
        if trade.status == "closed" and trade.close_time:
            close_date = trade.close_time.date()
            if close_date >= start_date:
                trade_events.append({
                    'date': close_date,
                    'time': trade.close_time,
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
    for trade_date in sorted(capital_records.keys()):
        available, position_val, total = capital_records[trade_date]
        result = await db.execute(
            select(CapitalHistory).where(
                CapitalHistory.user_id == user_id,
                CapitalHistory.date == trade_date
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            existing.capital = total
            existing.available_funds = available
            existing.position_value = position_val
        else:
            new_history = CapitalHistory(
                user_id=user_id,
                date=trade_date,
                capital=total,
                available_funds=available,
                position_value=position_val
            )
            db.add(new_history)
    
    await db.commit()
