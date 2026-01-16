from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, Date, UniqueConstraint, Index
from datetime import datetime
import os
from pathlib import Path

# 数据库配置：支持PostgreSQL和SQLite
# 优先使用PostgreSQL（生产环境），如果没有配置则使用SQLite（本地开发）
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # 使用PostgreSQL（生产环境）
    # DATABASE_URL格式：postgresql+asyncpg://user:password@host:port/database
    # 或者：postgresql://user:password@host:port/database（会自动转换为asyncpg）
    if DATABASE_URL.startswith("postgresql://"):
        # 转换为asyncpg驱动
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif not DATABASE_URL.startswith("postgresql+asyncpg://"):
        # 如果不是标准格式，尝试添加asyncpg
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    print(f"📦 [数据库] 使用PostgreSQL数据库")
    print(f"📦 [数据库] DATABASE_URL: {DATABASE_URL.split('@')[0]}@***")  # 隐藏密码
    DB_TYPE = "PostgreSQL"
else:
    # 使用SQLite（本地开发）
    DB_DIR = Path(os.getenv("DB_DIR", "."))
    DB_DIR.mkdir(parents=True, exist_ok=True)
    DATABASE_PATH = DB_DIR / "database.db"
    DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_PATH}"
    
    print(f"📦 [数据库] 使用SQLite数据库（本地开发）")
    print(f"📦 [数据库] 数据库文件路径: {DATABASE_PATH}")
    print(f"📦 [数据库] DB_DIR环境变量: {os.getenv('DB_DIR', '未设置（使用当前目录）')}")
    print(f"📦 [数据库] 数据库文件存在: {DATABASE_PATH.exists()}")
    if DATABASE_PATH.exists():
        import os as os_module
        file_size = os_module.path.getsize(DATABASE_PATH)
        print(f"📦 [数据库] 数据库文件大小: {file_size} 字节")
    DB_TYPE = "SQLite"

engine = create_async_engine(DATABASE_URL, echo=False)  # 关闭echo减少日志
try:
    from sqlalchemy.ext.asyncio import async_sessionmaker  # type: ignore

    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
except Exception:
    AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)
    last_login_at = Column(DateTime, nullable=True)
    is_paid = Column(Boolean, default=False)
    paid_until = Column(Date, nullable=True)
    plan = Column(String, default="free")
    total_paid = Column(Float, default=0.0)
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
    __table_args__ = (
        Index('idx_user_open_time', 'user_id', 'is_deleted', 'open_time'),
        Index('idx_user_strategy_open_time', 'user_id', 'strategy_id', 'is_deleted', 'open_time'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    strategy_id = Column(Integer, nullable=True, index=True)
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

class Strategy(Base):
    __tablename__ = "strategies"
    __table_args__ = (
        Index('idx_strategies_user_market', 'user_id', 'market'),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    name = Column(String, nullable=False)
    uid = Column(String, nullable=False, unique=True, index=True)
    market = Column(String, default="stock", index=True)
    initial_capital = Column(Float, nullable=True)
    initial_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class StrategyCapitalHistory(Base):
    __tablename__ = "strategy_capital_history"
    __table_args__ = (
        UniqueConstraint('user_id', 'strategy_id', 'date', name='_user_strategy_date_uc'),
        Index('idx_strategy_capital_user_strategy_date', 'user_id', 'strategy_id', 'date'),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    strategy_id = Column(Integer, nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    capital = Column(Float, nullable=False)
    available_funds = Column(Float, nullable=True)
    position_value = Column(Float, nullable=True, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

class ForexAccount(Base):
    __tablename__ = "forex_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, unique=True, index=True)
    currency = Column(String, default="USD")
    leverage = Column(Integer, default=100)
    initial_balance = Column(Float, default=10000)
    initial_date = Column(Date, nullable=True)
    balance = Column(Float, default=10000)
    equity = Column(Float, default=10000)
    margin = Column(Float, default=0)
    free_margin = Column(Float, default=10000)
    margin_level = Column(Float, default=0)
    max_drawdown = Column(Float, default=0)
    peak_equity = Column(Float, default=10000)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ForexTrade(Base):
    __tablename__ = "forex_trades"
    __table_args__ = (
        Index('idx_forex_user_open_time', 'user_id', 'is_deleted', 'open_time'),
        Index('idx_forex_user_strategy_open_time', 'user_id', 'strategy_id', 'is_deleted', 'open_time'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    strategy_id = Column(Integer, nullable=True, index=True)
    symbol = Column(String, nullable=False)
    side = Column(String, nullable=False)  # BUY | SELL
    lots = Column(Float, nullable=False)
    open_time = Column(DateTime, nullable=False, index=True)
    close_time = Column(DateTime)
    open_price = Column(Float, nullable=False)
    close_price = Column(Float)
    sl = Column(Float)
    tp = Column(Float)
    commission = Column(Float, default=0)
    swap = Column(Float, default=0)
    profit = Column(Float)
    notes = Column(Text)
    status = Column(String, default="open", index=True)
    is_deleted = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if DB_TYPE == "SQLite":
            result = await conn.exec_driver_sql("PRAGMA table_info(users)")
            cols = [row[1] for row in result.fetchall()]
            if "is_admin" not in cols:
                await conn.exec_driver_sql("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0")
            if "last_login_at" not in cols:
                await conn.exec_driver_sql("ALTER TABLE users ADD COLUMN last_login_at DATETIME")
            if "is_paid" not in cols:
                await conn.exec_driver_sql("ALTER TABLE users ADD COLUMN is_paid BOOLEAN DEFAULT 0")
            if "paid_until" not in cols:
                await conn.exec_driver_sql("ALTER TABLE users ADD COLUMN paid_until DATE")
            if "plan" not in cols:
                await conn.exec_driver_sql("ALTER TABLE users ADD COLUMN plan VARCHAR DEFAULT 'free'")
            if "total_paid" not in cols:
                await conn.exec_driver_sql("ALTER TABLE users ADD COLUMN total_paid FLOAT DEFAULT 0")

            result = await conn.exec_driver_sql("PRAGMA table_info(trades)")
            cols = [row[1] for row in result.fetchall()]
            if "strategy_id" not in cols:
                await conn.exec_driver_sql("ALTER TABLE trades ADD COLUMN strategy_id INTEGER")

            result = await conn.exec_driver_sql("PRAGMA table_info(forex_trades)")
            cols = [row[1] for row in result.fetchall()]
            if "strategy_id" not in cols:
                await conn.exec_driver_sql("ALTER TABLE forex_trades ADD COLUMN strategy_id INTEGER")

            result = await conn.exec_driver_sql("PRAGMA table_info(forex_accounts)")
            cols = [row[1] for row in result.fetchall()]
            if "initial_balance" not in cols:
                await conn.exec_driver_sql(
                    "ALTER TABLE forex_accounts ADD COLUMN initial_balance FLOAT DEFAULT 10000"
                )
                await conn.exec_driver_sql(
                    "UPDATE forex_accounts SET initial_balance = COALESCE(initial_balance, balance, 10000)"
                )
            if "initial_date" not in cols:
                await conn.exec_driver_sql("ALTER TABLE forex_accounts ADD COLUMN initial_date DATE")
                await conn.exec_driver_sql(
                    "UPDATE forex_accounts SET initial_date = COALESCE(initial_date, DATE(created_at), DATE('now'))"
                )
        else:
            await conn.exec_driver_sql("ALTER TABLE trades ADD COLUMN IF NOT EXISTS strategy_id INTEGER")
            await conn.exec_driver_sql("ALTER TABLE forex_trades ADD COLUMN IF NOT EXISTS strategy_id INTEGER")
            await conn.exec_driver_sql("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE")
            await conn.exec_driver_sql("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP")
            await conn.exec_driver_sql("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_paid BOOLEAN DEFAULT FALSE")
            await conn.exec_driver_sql("ALTER TABLE users ADD COLUMN IF NOT EXISTS paid_until DATE")
            await conn.exec_driver_sql("ALTER TABLE users ADD COLUMN IF NOT EXISTS plan VARCHAR DEFAULT 'free'")
            await conn.exec_driver_sql("ALTER TABLE users ADD COLUMN IF NOT EXISTS total_paid DOUBLE PRECISION DEFAULT 0")
