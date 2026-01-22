from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, Date, UniqueConstraint, Index, text
from datetime import datetime
import os
from pathlib import Path
import ssl as ssl_module
from urllib.parse import urlsplit, urlunsplit
import asyncio

# 数据库配置：支持PostgreSQL和SQLite
# 优先使用PostgreSQL（生产环境），如果没有配置则使用SQLite（本地开发）
DATABASE_URL = os.getenv("DATABASE_URL")

def _safe_database_url_for_log(database_url: str) -> str:
    try:
        parts = urlsplit(database_url)
        netloc = parts.netloc
        if "@" in netloc:
            userinfo, hostinfo = netloc.rsplit("@", 1)
            netloc = f"***@{hostinfo}"
        return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
    except Exception:
        return "***"

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
    print(f"📦 [数据库] DATABASE_URL: {_safe_database_url_for_log(DATABASE_URL)}")
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

DB_DIR = Path(os.getenv("DB_DIR", "."))
DB_DIR.mkdir(parents=True, exist_ok=True)
SQLITE_DATABASE_PATH = DB_DIR / "database.db"
SQLITE_DATABASE_URL = f"sqlite+aiosqlite:///{SQLITE_DATABASE_PATH}"

_node_env = (os.getenv("NODE_ENV", "") or "").strip().lower()
_default_fallback_to_sqlite = "false" if _node_env == "production" else "true"
_fallback_to_sqlite = (
    os.getenv("DB_FALLBACK_TO_SQLITE", _default_fallback_to_sqlite) or ""
).strip().lower() in {"1", "true", "yes", "on"}
_active_db_type = DB_TYPE
_sqlite_initialized = False
_sqlite_init_lock = asyncio.Lock()

engine_kwargs = {"echo": False}
sqlite_engine = create_async_engine(SQLITE_DATABASE_URL, echo=False)
try:
    from sqlalchemy.ext.asyncio import async_sessionmaker as _async_sessionmaker  # type: ignore

    SqliteSessionLocal = _async_sessionmaker(sqlite_engine, class_=AsyncSession, expire_on_commit=False)
except Exception:
    SqliteSessionLocal = sessionmaker(bind=sqlite_engine, class_=AsyncSession, expire_on_commit=False)

if DB_TYPE == "PostgreSQL":
    connect_timeout = int(os.getenv("DB_CONNECT_TIMEOUT", "60"))
    command_timeout = int(os.getenv("DB_COMMAND_TIMEOUT", "60"))
    connect_args = {"timeout": connect_timeout, "command_timeout": command_timeout}

    db_ssl = os.getenv("DB_SSL", "auto").strip().lower()
    if db_ssl not in {"0", "false", "no", "disable", "disabled"}:
        disable_ssl_verify = os.getenv("DISABLE_SSL_VERIFY", "false").strip().lower() in {"1", "true", "yes", "on"}
        db_ssl_verify = os.getenv("DB_SSL_VERIFY", "auto").strip().lower()
        ssl_context = None
        if db_ssl in {"verify", "verify-full", "verify_full", "strict"}:
            ssl_context = ssl_module.create_default_context()
        else:
            node_env = os.getenv("NODE_ENV", "").strip().lower()
            host = ""
            try:
                host = urlsplit(DATABASE_URL).hostname or ""
            except Exception:
                host = ""
            if node_env == "production" or host.endswith("supabase.co"):
                ssl_context = ssl_module.create_default_context()
        if ssl_context is not None:
            verify_enabled = db_ssl in {"verify", "verify-full", "verify_full", "strict"}
            if db_ssl_verify in {"1", "true", "yes", "on"}:
                verify_enabled = True
            if disable_ssl_verify or db_ssl_verify in {"0", "false", "no", "off", "disable", "disabled", "insecure", "allow"}:
                verify_enabled = False
            if not verify_enabled:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl_module.CERT_NONE
            connect_args["ssl"] = ssl_context

    engine_kwargs.update(
        {
            "pool_pre_ping": True,
            "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "1800")),
            "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "5")),
            "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "60")),
            "connect_args": connect_args,
        }
    )

engine = create_async_engine(DATABASE_URL, **engine_kwargs)  # 关闭echo减少日志
try:
    from sqlalchemy.ext.asyncio import async_sessionmaker  # type: ignore

    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
except Exception:
    AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
else:
    engine = sqlite_engine
    AsyncSessionLocal = SqliteSessionLocal

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

class PaymentOrder(Base):
    __tablename__ = "payment_orders"
    __table_args__ = (
        UniqueConstraint("order_no", name="uq_payment_orders_order_no"),
        Index("idx_payment_orders_user_created_at", "user_id", "created_at"),
        Index("idx_payment_orders_status_created_at", "status", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    order_no = Column(String, nullable=False, index=True)
    channel = Column(String, nullable=False)
    amount_cents = Column(Integer, nullable=False, default=0)
    currency = Column(String, nullable=False, default="CNY")
    plan = Column(String, nullable=False, default="pro")
    months = Column(Integer, nullable=False, default=1)
    status = Column(String, nullable=False, default="pending")
    note = Column(Text, nullable=True)
    approved_by_admin = Column(String, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class BillingPlanPrice(Base):
    __tablename__ = "billing_plan_prices"
    __table_args__ = (UniqueConstraint("plan", name="uq_billing_plan_prices_plan"),)

    id = Column(Integer, primary_key=True, index=True)
    plan = Column(String, nullable=False, index=True)
    unit_price_cents = Column(Integer, nullable=False, default=0)
    currency = Column(String, nullable=False, default="CNY")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
        Index('idx_trades_open_trade_id', 'user_id', 'strategy_id', 'open_trade_id'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    open_trade_id = Column(Integer, nullable=True, index=True)
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
    client_request_id = Column(String, nullable=True, index=True)
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
    client_request_id = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

async def _init_schema(conn, db_type: str) -> None:
    await conn.run_sync(Base.metadata.create_all)
    if db_type == "SQLite":
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
        if "client_request_id" not in cols:
            await conn.exec_driver_sql("ALTER TABLE trades ADD COLUMN client_request_id VARCHAR")
        if "open_trade_id" not in cols:
            await conn.exec_driver_sql("ALTER TABLE trades ADD COLUMN open_trade_id INTEGER")
        await conn.exec_driver_sql(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_trades_user_client_request_id ON trades(user_id, client_request_id) WHERE client_request_id IS NOT NULL"
        )
        await conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_trades_open_trade_id ON trades(user_id, strategy_id, open_trade_id)"
        )
        await conn.exec_driver_sql("UPDATE trades SET open_trade_id = id WHERE open_trade_id IS NULL")

        result = await conn.exec_driver_sql("PRAGMA table_info(forex_trades)")
        cols = [row[1] for row in result.fetchall()]
        if "strategy_id" not in cols:
            await conn.exec_driver_sql("ALTER TABLE forex_trades ADD COLUMN strategy_id INTEGER")
        if "client_request_id" not in cols:
            await conn.exec_driver_sql("ALTER TABLE forex_trades ADD COLUMN client_request_id VARCHAR")
        await conn.exec_driver_sql(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_forex_trades_user_client_request_id ON forex_trades(user_id, client_request_id) WHERE client_request_id IS NOT NULL"
        )

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
        return

    await conn.exec_driver_sql("ALTER TABLE trades ADD COLUMN IF NOT EXISTS strategy_id INTEGER")
    await conn.exec_driver_sql("ALTER TABLE forex_trades ADD COLUMN IF NOT EXISTS strategy_id INTEGER")
    await conn.exec_driver_sql("ALTER TABLE trades ADD COLUMN IF NOT EXISTS client_request_id VARCHAR")
    await conn.exec_driver_sql("ALTER TABLE forex_trades ADD COLUMN IF NOT EXISTS client_request_id VARCHAR")
    await conn.exec_driver_sql("ALTER TABLE trades ADD COLUMN IF NOT EXISTS open_trade_id INTEGER")
    await conn.exec_driver_sql(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_trades_user_client_request_id ON trades(user_id, client_request_id) WHERE client_request_id IS NOT NULL"
    )
    await conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS idx_trades_open_trade_id ON trades(user_id, strategy_id, open_trade_id)"
    )
    await conn.exec_driver_sql("UPDATE trades SET open_trade_id = id WHERE open_trade_id IS NULL")
    await conn.exec_driver_sql(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_forex_trades_user_client_request_id ON forex_trades(user_id, client_request_id) WHERE client_request_id IS NOT NULL"
    )
    await conn.exec_driver_sql("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE")
    await conn.exec_driver_sql("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP")
    await conn.exec_driver_sql("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_paid BOOLEAN DEFAULT FALSE")
    await conn.exec_driver_sql("ALTER TABLE users ADD COLUMN IF NOT EXISTS paid_until DATE")
    await conn.exec_driver_sql("ALTER TABLE users ADD COLUMN IF NOT EXISTS plan VARCHAR DEFAULT 'free'")
    await conn.exec_driver_sql("ALTER TABLE users ADD COLUMN IF NOT EXISTS total_paid DOUBLE PRECISION DEFAULT 0")

async def _ensure_sqlite_initialized() -> None:
    global _sqlite_initialized
    if _sqlite_initialized:
        return
    async with _sqlite_init_lock:
        if _sqlite_initialized:
            return
        async with sqlite_engine.begin() as conn:
            await _init_schema(conn, "SQLite")
        _sqlite_initialized = True

async def get_db():
    global _active_db_type
    if _active_db_type == "PostgreSQL":
        async with AsyncSessionLocal() as session:
            if not _fallback_to_sqlite:
                yield session
                return
            probe_timeout_s = float(os.getenv("DB_PROBE_TIMEOUT", "2.5"))
            try:
                await asyncio.wait_for(session.execute(text("SELECT 1")), timeout=probe_timeout_s)
            except Exception:
                _active_db_type = "SQLite"
            else:
                yield session
                return

    await _ensure_sqlite_initialized()
    async with SqliteSessionLocal() as session:
        yield session

async def init_db():
    async with engine.begin() as conn:
        await _init_schema(conn, DB_TYPE)
    if DB_TYPE != "SQLite":
        await _ensure_sqlite_initialized()
