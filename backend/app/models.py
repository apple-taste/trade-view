from pydantic import BaseModel, EmailStr
from datetime import datetime, date
from typing import Optional, Union, List

# 认证相关
class UserRegister(BaseModel):
    """用户注册模型"""
    username: str = "用户名，3-20个字符"
    email: EmailStr = "邮箱地址，用于登录和找回密码"
    password: str = "密码，建议至少8位"

    class Config:
        json_schema_extra = {
            "example": {
                "username": "trader001",
                "email": "trader@example.com",
                "password": "password123"
            }
        }

class UserLogin(BaseModel):
    """用户登录模型"""
    username: str = "用户名或邮箱"
    password: str = "密码"

    class Config:
        json_schema_extra = {
            "example": {
                "username": "trader001",
                "password": "password123"
            }
        }

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    email_alerts_enabled: Optional[bool] = False  # 邮箱提醒开关
    created_at: Optional[datetime] = None

class TokenResponse(BaseModel):
    token: str
    user: UserResponse

# 资金相关
class CapitalUpdate(BaseModel):
    capital: float
    date: Optional[str] = None  # 字符串类型，在路由中解析
class CapitalHistoryItem(BaseModel):
    date: date
    capital: float  # 总资产
    available_funds: Optional[float] = None  # 可用资金
    position_value: Optional[float] = None  # 持仓市值

# 交易记录相关
class TradeCreate(BaseModel):
    """创建交易记录模型"""
    stock_code: str = "股票代码，如：600879"
    stock_name: Optional[str] = None
    open_time: Optional[datetime] = None
    shares: Optional[int] = None  # 买入股数（可选，如果提供了单笔风险会自动计算）
    commission: Optional[float] = 0  # 总手续费（可选，系统会自动计算）
    buy_commission: Optional[float] = None  # 买入手续费（可选，系统会自动计算）
    buy_price: float = "实际买入价格"
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    stop_loss_alert: Optional[bool] = False
    take_profit_alert: Optional[bool] = False
    notes: Optional[str] = None
    risk_per_trade: Optional[float] = None  # 单笔风险金额（可选，用于自动计算手数）

    class Config:
        json_schema_extra = {
            "example": {
                "stock_code": "600879",
                "stock_name": "航空电子",
                "open_time": "2024-01-11T10:00:00",
                "shares": 1000,
                "commission": 5.0,
                "buy_price": 15.50,
                "stop_loss_price": 14.00,
                "take_profit_price": 18.00,
                "stop_loss_alert": True,
                "take_profit_alert": True,
                "notes": "看好航空电子行业发展"
            }
        }

class TradeUpdate(BaseModel):
    stock_code: Optional[str] = None
    stock_name: Optional[str] = None
    open_time: Optional[datetime] = None
    close_time: Optional[datetime] = None
    shares: Optional[int] = None
    commission: Optional[float] = None
    buy_commission: Optional[float] = None  # 买入手续费
    sell_commission: Optional[float] = None  # 卖出手续费
    buy_price: Optional[float] = None
    sell_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    stop_loss_alert: Optional[bool] = None
    take_profit_alert: Optional[bool] = None
    current_price: Optional[float] = None
    holding_days: Optional[int] = None
    order_result: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None

class TradeResponse(BaseModel):
    id: int
    user_id: int
    stock_code: str
    stock_name: Optional[str]
    open_time: datetime
    close_time: Optional[datetime]
    shares: int
    commission: float  # 总手续费
    buy_commission: Optional[float] = None  # 买入手续费
    sell_commission: Optional[float] = None  # 卖出手续费
    buy_price: float
    sell_price: Optional[float]
    stop_loss_price: Optional[float]
    take_profit_price: Optional[float]
    stop_loss_alert: bool
    take_profit_alert: bool
    current_price: Optional[float]
    holding_days: int
    order_result: Optional[str]
    notes: Optional[str]
    status: str
    risk_reward_ratio: Optional[float] = None  # 风险回报比（兼容旧版，等同于theoretical_risk_reward_ratio）
    theoretical_risk_reward_ratio: Optional[float] = None  # 理论风险回报比
    actual_risk_reward_ratio: Optional[float] = None  # 实际风险回报比
    price_source: Optional[str] = None  # 价格来源
    profit_loss: Optional[float] = None  # 盈亏金额
    created_at: datetime
    updated_at: datetime

class PaginatedTradeResponse(BaseModel):
    items: List[TradeResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

# 持仓相关
class PositionUpdate(BaseModel):
    current_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    stop_loss_alert: Optional[bool] = None
    take_profit_alert: Optional[bool] = None

class TakeProfitRequest(BaseModel):
    sell_price: float
    close_date: Optional[str] = None  # 离场日期（YYYY-MM-DD格式，北京时间），可选，默认使用当前时间

class StopLossRequest(BaseModel):
    sell_price: float
    close_date: Optional[str] = None  # 离场日期（YYYY-MM-DD格式，北京时间），可选，默认使用当前时间

# AI分析相关
class AnalysisSummary(BaseModel):
    totalTrades: int
    winRate: float
    totalProfit: float
    averageHoldingDays: float
    stopLossExecuted: int
    takeProfitExecuted: int
    profitLossRatio: float = 0.0  # 盈亏比

class DetailedAnalysis(BaseModel):
    stop_loss_analysis: str
    take_profit_analysis: str
    entry_price_analysis: str
    profit_loss_ratio_analysis: str
    capital_management: str
    key_insights: list[str]
    recommendations: list[str]

class AnalysisResponse(BaseModel):
    summary: AnalysisSummary
    detailed_analysis: Optional[DetailedAnalysis] = None  # AI详细分析

class ForexAccountUpdate(BaseModel):
    currency: Optional[str] = None
    leverage: Optional[int] = None
    balance: Optional[float] = None

class ForexAccountReset(BaseModel):
    balance: float
    date: Optional[date] = None
    currency: Optional[str] = None
    leverage: Optional[int] = None

class ForexAccountInitialUpdate(BaseModel):
    initial_balance: float
    initial_date: Optional[date] = None

class ForexAccountResponse(BaseModel):
    user_id: int
    currency: str
    leverage: int
    initial_balance: float
    initial_date: Optional[date] = None
    balance: float
    equity: float
    margin: float
    free_margin: float
    margin_level: float
    max_drawdown: float
    peak_equity: float
    updated_at: datetime

class ForexTradeCreate(BaseModel):
    symbol: str
    side: str
    lots: float
    open_time: Optional[datetime] = None
    open_price: float
    sl: Optional[float] = None
    tp: Optional[float] = None
    commission: Optional[float] = 0
    swap: Optional[float] = 0
    notes: Optional[str] = None

class ForexTradeUpdate(BaseModel):
    sl: Optional[float] = None
    tp: Optional[float] = None
    notes: Optional[str] = None

class ForexTradeClose(BaseModel):
    close_time: Optional[datetime] = None
    close_price: float
    swap: Optional[float] = None
    commission: Optional[float] = None

class ForexTradeResponse(BaseModel):
    id: int
    user_id: int
    symbol: str
    side: str
    lots: float
    open_time: datetime
    close_time: Optional[datetime]
    open_price: float
    close_price: Optional[float]
    sl: Optional[float]
    tp: Optional[float]
    commission: float
    swap: float
    profit: Optional[float]
    notes: Optional[str]
    status: str
    theoretical_risk_reward_ratio: Optional[float] = None
    actual_risk_reward_ratio: Optional[float] = None
    created_at: datetime
    updated_at: datetime

class ForexPaginatedTradeResponse(BaseModel):
    items: List[ForexTradeResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

class ForexCapitalPoint(BaseModel):
    date: date
    equity: float
    balance: float

class ForexQuoteResponse(BaseModel):
    symbol: str
    price: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    asof: datetime
    source: str
    error: Optional[str] = None
