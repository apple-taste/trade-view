from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import pandas as pd
import logging
import os
import time
import json
from datetime import datetime, date

from app.database import get_db, Trade, CapitalHistory, ForexTrade, ForexAccount
from app.middleware.auth import get_current_user
from app.models import AnalysisResponse, AnalysisSummary, DetailedAnalysis
from app.database import User
from app.services.ai_analyzer import ai_analyzer

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get(
    "/trade-summary",
    response_model=AnalysisResponse,
    summary="交易分析（统计+可选AI分析）",
    description="""
    对用户的交易历史进行分析。
    
    **统计摘要**（本地计算，无需AI）:
    - 总交易次数、胜率、累计盈亏、平均持仓天数、盈亏比等
    - 这些数据通过开仓历史计算得出，不调用AI
    
    **AI详细分析**（可选，需要时调用）:
    - 通过 `use_ai=true` 参数控制是否调用AI
    - 只有用户点击AI分析时，才会把开仓历史和资金曲线数据传给AI
    - AI生成：止损止盈分析、入场价格分析、盈亏比分析、资金管理建议
    
    **参数**:
    - **use_ai**: 是否调用AI分析（默认false，只返回统计摘要）
    
    如果没有交易记录，返回提示信息。
    """,
    responses={
        200: {
            "description": "分析成功",
            "content": {
                "application/json": {
                    "example": {
                        "summary": {
                            "totalTrades": 10,
                            "winRate": 60.0,
                            "totalProfit": 5000.0,
                            "averageHoldingDays": 15.5,
                            "stopLossExecuted": 2,
                            "takeProfitExecuted": 4,
                            "profitLossRatio": 1.8
                        },
                        "insights": [
                            "当前胜率为 60.00%，表现良好",
                            "累计盈利 5000.00 元"
                        ],
                        "recommendations": [
                            "继续保持当前交易策略"
                        ],
                        "detailed_analysis": {
                            "stop_loss_analysis": "止损价格分析...",
                            "take_profit_analysis": "止盈价格分析...",
                            "entry_price_analysis": "入场价格分析...",
                            "profit_loss_ratio_analysis": "盈亏比分析...",
                            "capital_management": "资金管理建议...",
                            "key_insights": ["洞察1", "洞察2"],
                            "recommendations": ["建议1", "建议2"]
                        }
                    }
                }
            }
        }
    }
)
async def analyze_trades(
    use_ai: bool = False,  # 是否调用AI分析，默认False（只返回统计摘要）
    system_mode: str = "stock",  # 系统模式：stock 或 forex
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    logger.info(f"🤖 [AI分析] 用户 {current_user.username} 开始交易分析")
    
    trades = []
    capital_history = []

    if system_mode == "forex":
        # 外汇模式：读取外汇交易与账户初始资金，按关闭日期构造资金曲线
        result = await db.execute(
            select(ForexTrade)
            .where(
                ForexTrade.user_id == current_user.id,
                ForexTrade.is_deleted == False
            )
            .order_by(ForexTrade.open_time.desc())
        )
        trades = result.scalars().all()

        acc_result = await db.execute(
            select(ForexAccount).where(ForexAccount.user_id == current_user.id)
        )
        account = acc_result.scalar_one_or_none()
        if account:
            anchor_date: date = account.initial_date or datetime.utcnow().date()
            running = float(account.initial_balance or 0)
            points_by_date: dict[date, float] = {anchor_date: running}

            closed_result = await db.execute(
                select(ForexTrade)
                .where(
                    ForexTrade.user_id == current_user.id,
                    ForexTrade.is_deleted == False,
                    ForexTrade.status == "closed",
                    ForexTrade.close_time.isnot(None),
                )
                .order_by(ForexTrade.close_time.asc())
            )
            closed = closed_result.scalars().all()
            for t in closed:
                d = t.close_time.date() if t.close_time else anchor_date
                if d < anchor_date:
                    continue
                running += float(t.profit or 0)
                points_by_date[d] = running

            for d in sorted(points_by_date.keys()):
                capital_history.append(type("CapitalPoint", (), {"date": d, "capital": points_by_date[d]}))
    else:
        # A股模式：保持原逻辑
        result = await db.execute(
            select(Trade)
            .where(
                Trade.user_id == current_user.id,
                Trade.is_deleted == False  # 排除已删除的记录
            )
            .order_by(Trade.open_time.desc())
        )
        trades = result.scalars().all()
        capital_result = await db.execute(
            select(CapitalHistory).where(CapitalHistory.user_id == current_user.id).order_by(CapitalHistory.date.asc())
        )
        capital_history = capital_result.scalars().all()
    
    if not trades:
        logger.info(f"⚠️ [AI分析] 用户 {current_user.username} 没有交易记录")
        # 如果没有交易记录，但用户请求AI分析，返回提示信息
        if use_ai:
            return AnalysisResponse(
                summary=AnalysisSummary(
                    totalTrades=0,
                    winRate=0,
                    totalProfit=0,
                    averageHoldingDays=0,
                    stopLossExecuted=0,
                    takeProfitExecuted=0,
                    profitLossRatio=0.0
                ),
                detailed_analysis=DetailedAnalysis(
                    stop_loss_analysis="当前无交易记录",
                    take_profit_analysis="当前无交易记录",
                    entry_price_analysis="当前无交易记录",
                    profit_loss_ratio_analysis="当前无交易记录",
                    capital_management="当前无交易记录",
                    key_insights=["当前无交易记录"],
                    recommendations=["请先进行交易后再进行AI分析"]
                )
            )
        # 如果没有交易记录，且不请求AI分析，只返回统计摘要
        return AnalysisResponse(
            summary=AnalysisSummary(
                totalTrades=0,
                winRate=0,
                totalProfit=0,
                averageHoldingDays=0,
                stopLossExecuted=0,
                takeProfitExecuted=0,
                profitLossRatio=0.0
            )
        )
    
    # 转换为DataFrame便于分析
    trades_data = []
    for trade in trades:
        if system_mode == "forex":
            if trade.status == "closed" and trade.close_price:
                profit = float(trade.profit or 0)
                holding_days = 0
                if trade.open_time and trade.close_time:
                    holding_days = max(0, (trade.close_time - trade.open_time).days)
                trades_data.append({
                    "id": trade.id,
                    "stock_code": trade.symbol,  # 复用字段名以兼容AI分析器
                    "stock_name": trade.symbol,
                    "buy_price": float(trade.open_price),
                    "sell_price": float(trade.close_price),
                    "stop_loss_price": float(trade.sl) if trade.sl is not None else None,
                    "take_profit_price": float(trade.tp) if trade.tp is not None else None,
                    "shares": float(trade.lots),  # lots作为数量
                    "commission": float(trade.commission or 0),
                    "buy_commission": 0.0,
                    "sell_commission": float(trade.commission or 0),
                    "profit": profit,
                    "profit_loss": profit,
                    "holding_days": holding_days,
                    "order_result": None,
                    "status": trade.status,
                    "open_time": trade.open_time.isoformat() if trade.open_time else None,
                    "close_time": trade.close_time.isoformat() if trade.close_time else None,
                    "notes": trade.notes or "",
                    "theoretical_risk_reward_ratio": None,
                    "actual_risk_reward_ratio": None
                })
        else:
            if trade.status == "closed" and trade.sell_price:
                # 优先使用profit_loss字段，如果没有则计算
                if trade.profit_loss is not None:
                    profit = trade.profit_loss
                else:
                    profit = (trade.sell_price - trade.buy_price) * trade.shares - (trade.commission or 0)
                
                trades_data.append({
                    "id": trade.id,
                    "stock_code": trade.stock_code,
                    "stock_name": trade.stock_name,
                    "buy_price": trade.buy_price,
                    "sell_price": trade.sell_price,
                    "stop_loss_price": trade.stop_loss_price,
                    "take_profit_price": trade.take_profit_price,
                    "shares": trade.shares,
                    "commission": trade.commission or 0,
                    "buy_commission": trade.buy_commission or 0,
                    "sell_commission": trade.sell_commission or 0,
                    "profit": profit,
                    "profit_loss": trade.profit_loss,  # 保存原始盈亏字段
                    "holding_days": trade.holding_days or 0,
                    "order_result": trade.order_result,
                    "status": trade.status,
                    "open_time": trade.open_time.isoformat() if trade.open_time else None,
                    "close_time": trade.close_time.isoformat() if trade.close_time else None,
                    "notes": trade.notes or "",  # 备注字段（重要：AI需要看到备注）
                    "theoretical_risk_reward_ratio": trade.theoretical_risk_reward_ratio,
                    "actual_risk_reward_ratio": trade.actual_risk_reward_ratio
                })
    
    if not trades_data:
        logger.info(f"⚠️ [AI分析] 用户 {current_user.username} 没有已平仓的交易记录")
        # 如果没有已平仓的交易记录，但用户请求AI分析，返回提示信息
        if use_ai:
            return AnalysisResponse(
                summary=AnalysisSummary(
                    totalTrades=0,
                    winRate=0,
                    totalProfit=0,
                    averageHoldingDays=0,
                    stopLossExecuted=0,
                    takeProfitExecuted=0,
                    profitLossRatio=0.0
                ),
                detailed_analysis=DetailedAnalysis(
                    stop_loss_analysis="当前无已平仓的交易记录",
                    take_profit_analysis="当前无已平仓的交易记录",
                    entry_price_analysis="当前无已平仓的交易记录",
                    profit_loss_ratio_analysis="当前无已平仓的交易记录",
                    capital_management="当前无已平仓的交易记录",
                    key_insights=["当前无已平仓的交易记录"],
                    recommendations=["请先完成交易后再进行AI分析"]
                )
            )
        # 如果没有已平仓的交易记录，且不请求AI分析，只返回统计摘要
        return AnalysisResponse(
            summary=AnalysisSummary(
                totalTrades=0,
                winRate=0,
                totalProfit=0,
                averageHoldingDays=0,
                stopLossExecuted=0,
                takeProfitExecuted=0,
                profitLossRatio=0.0
            )
        )
    
    df = pd.DataFrame(trades_data)
    
    # 计算统计数据
    total_trades = len(df)
    win_trades = len(df[df["profit"] > 0])
    win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0
    total_profit = df["profit"].sum()
    avg_holding_days = df["holding_days"].mean()
    
    stop_loss_executed = len(df[df["order_result"] == "止损"])
    take_profit_executed = len(df[df["order_result"] == "止盈"])
    
    # 计算盈亏比
    avg_win = df[df["profit"] > 0]["profit"].mean() if win_trades > 0 else 0
    avg_loss = abs(df[df["profit"] < 0]["profit"].mean()) if (total_trades - win_trades) > 0 else 0
    profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0.0
    
    # 统计摘要（本地计算，不调用AI）
    summary = AnalysisSummary(
        totalTrades=total_trades,
        winRate=round(win_rate, 2),
        totalProfit=round(total_profit, 2),
        averageHoldingDays=round(avg_holding_days, 1),
        stopLossExecuted=stop_loss_executed,
        takeProfitExecuted=take_profit_executed,
        profitLossRatio=round(profit_loss_ratio, 2)
    )
    
    # AI详细分析（可选，只有用户点击AI分析时才调用）
    detailed_analysis = None
    if use_ai:
        # 准备资金历史数据（传给AI）
        capital_data = []
        if capital_history:
            capital_data = [
                {"date": str(h.date), "capital": float(h.capital)}
                for h in capital_history
            ]
        
        # 调用AI分析（传入开仓历史和资金曲线数据）
        logger.info("=" * 80)
        logger.info(f"🤖 [AI分析] ========== 开始AI深度分析 ==========")
        logger.info("=" * 80)
        logger.info(f"👤 [AI分析] 用户: {current_user.username} (ID: {current_user.id})")
        logger.info(f"📅 [AI分析] 请求时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("")
        logger.info("=" * 80)
        logger.info("📊 [AI分析] ========== 输入数据统计 ==========")
        logger.info("=" * 80)
        logger.info(f"📈 [AI分析] 交易记录:")
        logger.info(f"   • 总交易数: {len(trades_data)}条")
        logger.info(f"   • 已平仓交易: {sum(1 for t in trades_data if t.get('status') == 'closed')}条")
        logger.info(f"   • 盈利交易: {sum(1 for t in trades_data if t.get('profit', 0) > 0)}条")
        logger.info(f"   • 亏损交易: {sum(1 for t in trades_data if t.get('profit', 0) < 0)}条")
        logger.info(f"   • 止损执行: {sum(1 for t in trades_data if t.get('order_result') == '止损')}次")
        logger.info(f"   • 止盈执行: {sum(1 for t in trades_data if t.get('order_result') == '止盈')}次")
        logger.info("")
        logger.info(f"💰 [AI分析] 资金曲线:")
        logger.info(f"   • 资金曲线数据点: {len(capital_data)}条")
        if capital_data:
            initial = capital_data[0].get('capital', 0)
            current = capital_data[-1].get('capital', 0) if capital_data else 0
            change = current - initial
            change_pct = (change / initial * 100) if initial > 0 else 0
            logger.info(f"   • 初始资金: {initial:.2f}元")
            logger.info(f"   • 当前资金: {current:.2f}元")
            logger.info(f"   • 资金变化: {change:+.2f}元 ({change_pct:+.2f}%)")
        logger.info("")
        logger.info("=" * 80)
        logger.info("📥 [AI分析] ========== 输入数据详情（前5条交易） ==========")
        logger.info("=" * 80)
        notes_count = sum(1 for t in trades_data if t.get('notes'))
        logger.info(f"📝 [AI分析] 备注统计: {notes_count}/{len(trades_data)}条交易有备注")
        logger.info("")
        for i, trade in enumerate(trades_data[:5], 1):
            logger.info(f"交易 #{i}:")
            logger.info(f"   • 股票代码: {trade.get('stock_code', 'N/A')}")
            logger.info(f"   • 股票名称: {trade.get('stock_name', 'N/A')}")
            logger.info(f"   • 买入价: {trade.get('buy_price', 0):.2f}元")
            logger.info(f"   • 卖出价: {trade.get('sell_price', 0):.2f}元")
            logger.info(f"   • 盈亏: {trade.get('profit', 0):+.2f}元")
            logger.info(f"   • 订单结果: {trade.get('order_result', 'N/A')}")
            if trade.get('notes'):
                logger.info(f"   • 备注: {trade.get('notes', '')[:100]}...")
            logger.info("")
        logger.info("=" * 80)
        logger.info("🔄 [AI分析] ========== 数据流向 ==========")
        logger.info("=" * 80)
        logger.info("📥 数据输入:")
        logger.info(f"   1. 交易数据 → AI分析器 ({len(trades_data)}条记录)")
        logger.info(f"   2. 资金曲线 → AI分析器 ({len(capital_data)}条数据)")
        logger.info("")
        logger.info("🌐 API调用:")
        logger.info("   3. AI分析器 → ChatGPT-5 API")
        logger.info("   4. ChatGPT-5 API → 返回分析结果")
        logger.info("")
        logger.info("📤 数据输出:")
        logger.info("   5. 解析AI响应 → 结构化分析结果")
        logger.info("   6. 返回给前端 → 用户查看")
        logger.info("")
        logger.info("=" * 80)
        
        try:
            analysis_start = time.time()
            detailed_analysis_result = await ai_analyzer.analyze_trades_with_ai(trades_data, capital_data)
            analysis_time = time.time() - analysis_start
            
            # 构建详细分析对象
            try:
                detailed_analysis = DetailedAnalysis(**detailed_analysis_result)
                logger.info("=" * 80)
                logger.info("✅ [AI分析] ========== AI分析完成 ==========")
                logger.info("=" * 80)
                logger.info(f"⏱️ [AI分析] 总耗时: {analysis_time:.2f}秒")
                logger.info("")
                logger.info("=" * 80)
                logger.info("📤 [AI分析] ========== 输出数据统计 ==========")
                logger.info("=" * 80)
                logger.info(f"📝 [AI分析] 分析结果字段:")
                logger.info(f"   • 止损分析: {len(detailed_analysis.stop_loss_analysis)}字符")
                logger.info(f"   • 止盈分析: {len(detailed_analysis.take_profit_analysis)}字符")
                logger.info(f"   • 入场分析: {len(detailed_analysis.entry_price_analysis)}字符")
                logger.info(f"   • 盈亏比分析: {len(detailed_analysis.profit_loss_ratio_analysis)}字符")
                logger.info(f"   • 资金管理: {len(detailed_analysis.capital_management)}字符")
                logger.info(f"   • 关键洞察: {len(detailed_analysis.key_insights)}条")
                logger.info(f"   • 建议: {len(detailed_analysis.recommendations)}条")
                logger.info("")
                logger.info("=" * 80)
                logger.info("📤 [AI分析] ========== 输出数据预览 ==========")
                logger.info("=" * 80)
                logger.info("💡 [AI分析] 关键洞察:")
                for i, insight in enumerate(detailed_analysis.key_insights[:3], 1):
                    logger.info(f"   {i}. {insight[:100]}...")
                logger.info("")
                logger.info("💡 [AI分析] 核心建议:")
                for i, rec in enumerate(detailed_analysis.recommendations[:3], 1):
                    logger.info(f"   {i}. {rec[:100]}...")
                logger.info("")
                logger.info("=" * 80)
                logger.info("🔄 [AI分析] ========== 数据流向确认 ==========")
                logger.info("=" * 80)
                logger.info("✅ 数据流向完整:")
                logger.info("   ✅ 输入数据已发送到ChatGPT-5")
                logger.info("   ✅ ChatGPT-5已返回分析结果")
                logger.info("   ✅ 分析结果已解析并结构化")
                logger.info("   ✅ 准备返回给前端")
                logger.info("")
                logger.info("=" * 80)
            except Exception as e:
                logger.warning("=" * 80)
                logger.warning(f"⚠️ [AI分析] 构建详细分析对象失败")
                logger.warning(f"⚠️ [AI分析] 错误: {e}")
                logger.warning(f"📋 [AI分析] 返回的原始数据键: {list(detailed_analysis_result.keys())}")
                logger.warning("=" * 80)
        except Exception as e:
            logger.error("=" * 80)
            logger.error(f"❌ [AI分析] AI分析失败")
            logger.error(f"❌ [AI分析] 错误类型: {type(e).__name__}")
            logger.error(f"❌ [AI分析] 错误详情: {str(e)}")
            logger.error("=" * 80, exc_info=True)
    else:
        logger.info(f"📊 [统计] 用户 {current_user.username} 只请求统计摘要，不调用AI")
    
    logger.info(f"✅ [分析完成] 用户 {current_user.username} 交易分析完成")
    
    return AnalysisResponse(
        summary=summary,
        detailed_analysis=detailed_analysis
    )

@router.get(
    "/test-chatgpt",
    summary="测试ChatGPT-5连接（无需认证）",
    description="""
    测试ChatGPT-5 API连接状态。
    
    **功能**:
    - 检查AI_BUILDER_TOKEN是否配置
    - 测试API连接是否正常
    - 发送一个简单的测试请求
    - 返回连接状态和响应信息
    
    **用途**:
    - 在Swagger UI中快速测试ChatGPT连接（无需登录）
    - 调试API配置问题
    - 验证Token是否有效
    
    **注意**: 此端点不需要认证，可以直接测试。
    
    **返回信息**:
    - `status`: 连接状态 ("success" 或 "error")
    - `token_configured`: Token是否已配置
    - `api_url`: API端点地址
    - `model`: 使用的模型名称
    - `response_time`: 响应时间（秒）
    - `message`: 详细消息
    - `test_response`: 测试响应内容（如果成功）
    """,
    responses={
        200: {
            "description": "测试完成",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "token_configured": True,
                        "api_url": "https://space.ai-builders.com/backend/v1/chat/completions",
                        "model": "gpt-5",
                        "response_time": 2.5,
                        "message": "ChatGPT-5连接成功",
                        "test_response": "你好！我是ChatGPT-5..."
                    }
                }
            }
        }
    },
    tags=["AI分析"]
)
async def test_chatgpt_connection():
    """
    测试ChatGPT-5 API连接（无需认证）
    
    用于在Swagger UI中快速验证ChatGPT连接是否正常。
    此端点不需要认证，可以直接访问测试。
    """
    logger.info("=" * 60)
    logger.info(f"🧪 [ChatGPT测试] 开始测试ChatGPT-5连接（无需认证）")
    logger.info("=" * 60)
    
    # 检查Token配置
    api_key = os.getenv("AI_BUILDER_TOKEN", "")
    token_configured = bool(api_key)
    
    logger.info(f"🔑 [ChatGPT测试] Token配置状态: {'✅ 已配置' if token_configured else '❌ 未配置'}")
    if token_configured:
        logger.info(f"🔑 [ChatGPT测试] Token前缀: {api_key[:20]}...")
    else:
        logger.warning("⚠️ [ChatGPT测试] AI_BUILDER_TOKEN未设置")
        return {
            "status": "error",
            "token_configured": False,
            "api_url": "N/A",
            "model": "gpt-5",
            "response_time": 0,
            "message": "AI_BUILDER_TOKEN未配置，请在.env文件中设置",
            "test_response": None
        }
    
    # 测试API连接（与参考代码格式保持一致）
    base_url = "https://space.ai-builders.com/backend"
    chat_url = f"{base_url}/v1/chat/completions"
    model = "gpt-5"
    test_message = "你好，请用一句话介绍你自己。"
    
    logger.info(f"🌐 [ChatGPT测试] API端点: {chat_url}")
    logger.info(f"🤖 [ChatGPT测试] 模型: {model}")
    logger.info(f"📝 [ChatGPT测试] 测试消息: {test_message}")
    
    start_time = time.time()
    
    try:
        import aiohttp
        import ssl
        
        # SSL配置：开发环境可以禁用SSL验证
        disable_ssl_verify = os.getenv("DISABLE_SSL_VERIFY", "false").lower() == "true"
        
        if disable_ssl_verify:
            logger.warning("⚠️ [ChatGPT测试] SSL证书验证已禁用（仅用于开发环境）")
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            connector = aiohttp.TCPConnector(ssl=ssl_context)
        else:
            connector = None  # 使用默认SSL上下文
        
        async with aiohttp.ClientSession(connector=connector) as session:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # 使用max_tokens而不是max_completion_tokens（与参考代码一致）
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个友好的AI助手。"
                    },
                    {
                        "role": "user",
                        "content": test_message
                    }
                ],
                "temperature": 1.0,
                "max_tokens": 500  # 测试用，避免输出限制（使用max_tokens，与参考代码一致）
            }
            
            logger.info(f"📤 [ChatGPT测试] 发送请求...")
            logger.info(f"📤 [ChatGPT测试] 请求URL: {chat_url}")
            logger.info(f"📤 [ChatGPT测试] Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
            logger.info(f"📤 [ChatGPT测试] 请求头: Authorization: Bearer {api_key[:20]}...")
            
            async with session.post(
                chat_url,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                response_time = time.time() - start_time
                
                logger.info(f"📥 [ChatGPT测试] 响应状态码: {response.status}")
                logger.info(f"⏱️ [ChatGPT测试] 响应时间: {response_time:.2f}秒")
                
                if response.status == 200:
                    result = await response.json()
                    ai_response = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    
                    logger.info("=" * 60)
                    logger.info("✅ [ChatGPT测试] ChatGPT-5连接成功！")
                    logger.info(f"📝 [ChatGPT测试] 响应内容: {ai_response[:200]}...")
                    logger.info("=" * 60)
                    
                    return {
                        "status": "success",
                        "token_configured": True,
                        "api_url": chat_url,
                        "model": model,
                        "response_time": round(response_time, 2),
                        "message": "ChatGPT-5连接成功",
                        "test_response": ai_response,
                        "response_status": response.status
                    }
                else:
                    error_text = await response.text()
                    logger.error("=" * 60)
                    logger.error(f"❌ [ChatGPT测试] API错误: {response.status}")
                    logger.error(f"❌ [ChatGPT测试] 错误详情: {error_text}")
                    logger.error("=" * 60)
                    
                    return {
                        "status": "error",
                        "token_configured": True,
                        "api_url": chat_url,
                        "model": model,
                        "response_time": round(response_time, 2),
                        "message": f"API请求失败: HTTP {response.status}",
                        "test_response": None,
                        "error_detail": error_text[:500]
                    }
                    
    except aiohttp.ClientError as e:
        response_time = time.time() - start_time
        logger.error("=" * 60)
        logger.error(f"❌ [ChatGPT测试] 网络错误: {type(e).__name__}")
        logger.error(f"❌ [ChatGPT测试] 错误详情: {str(e)}")
        logger.error("=" * 60)
        
        return {
            "status": "error",
            "token_configured": True,
            "api_url": chat_url,
            "model": model,
            "response_time": round(response_time, 2),
            "message": f"网络连接错误: {type(e).__name__}",
            "test_response": None,
            "error_detail": str(e)
        }
        
    except Exception as e:
        response_time = time.time() - start_time
        logger.error("=" * 60)
        logger.error(f"❌ [ChatGPT测试] 未知错误: {type(e).__name__}")
        logger.error(f"❌ [ChatGPT测试] 错误详情: {str(e)}", exc_info=True)
        logger.error("=" * 60)
        
        return {
            "status": "error",
            "token_configured": True,
            "api_url": chat_url,
            "model": model,
            "response_time": round(response_time, 2),
            "message": f"测试失败: {type(e).__name__}",
            "test_response": None,
            "error_detail": str(e)
        }
