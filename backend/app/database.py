from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, Date, UniqueConstraint
from datetime import datetime

DATABASE_URL = "sqlite+aiosqlite:///./database.db"

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    # 初始入金锚点（用于"清空交易→恢复初始资金"以及资金曲线重算起点）
    initial_capital = Column(Float, nullable=True)
    initial_capital_date = Column(Date, nullable=True)
    # 邮箱提醒设置
    email_alerts_enabled = Column(Boolean, default=False)  # 是否启用邮箱提醒
    created_at = Column(DateTime, default=datetime.utcnow)

class CapitalHistory(Base):
    __tablename__ = "capital_history"
    __table_args__ = (UniqueConstraint('user_id', 'date', name='_user_date_uc'),)
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    capital = Column(Float, nullable=False)  # 总资产（兼容旧数据）
    available_funds = Column(Float, nullable=True)  # 可用资金
    position_value = Column(Float, nullable=True, default=0.0)  # 持仓市值
    created_at = Column(DateTime, default=datetime.utcnow)

class Trade(Base):
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    stock_code = Column(String, nullable=False)
    stock_name = Column(String)
    open_time = Column(DateTime, nullable=False, index=True)
    close_time = Column(DateTime)
    shares = Column(Integer, nullable=False)
    commission = Column(Float, default=0)  # 总手续费（兼容旧数据，等于buy_commission + sell_commission）
    buy_commission = Column(Float, default=0)  # 买入手续费
    sell_commission = Column(Float, default=0)  # 卖出手续费
    buy_price = Column(Float, nullable=False)
    sell_price = Column(Float)
    stop_loss_price = Column(Float)
    take_profit_price = Column(Float)
    stop_loss_alert = Column(Boolean, default=False)
    take_profit_alert = Column(Boolean, default=False)
    current_price = Column(Float)
    holding_days = Column(Integer, default=0)
    order_result = Column(String)
    profit_loss = Column(Float)  # 盈亏金额（平仓时计算：卖出价*手数 - 买入价*手数 - 手续费）
    theoretical_risk_reward_ratio = Column(Float)  # 理论风险回报比：(止盈价-入场价)/(入场价-止损价)
    actual_risk_reward_ratio = Column(Float)  # 实际风险回报比：平仓后根据实际离场价计算
    notes = Column(Text)
    status = Column(String, default="open", index=True)
    is_deleted = Column(Boolean, default=False, index=True)  # 软删除标记
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
