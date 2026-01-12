from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import uvicorn
import logging
import time
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from app.database import init_db
from app.routers import auth, user, trades, positions, analysis, price
from app.services.price_monitor import price_monitor
from app.services.alert_monitor import alert_monitor

# 加载环境变量（必须在其他导入之前）
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    logger_temp = logging.getLogger(__name__)
    logger_temp.info(f"✅ 已加载环境变量文件: {env_path}")
else:
    logger_temp = logging.getLogger(__name__)
    logger_temp.warning(f"⚠️ 环境变量文件不存在: {env_path}")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('backend.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 80)
    logger.info("🚀 启动 A股交易管理系统后端服务")
    logger.info("=" * 80)
    
    # 检查环境变量加载
    logger.info("🔍 [环境变量] 检查环境变量配置...")
    env_file = Path(__file__).parent / '.env'
    logger.info(f"📄 [环境变量] .env文件路径: {env_file}")
    logger.info(f"📄 [环境变量] .env文件存在: {'✅ 是' if env_file.exists() else '❌ 否'}")
    
    # 检查关键环境变量
    ai_token = os.getenv("AI_BUILDER_TOKEN", "")
    smtp_server = os.getenv("SMTP_SERVER", "")
    
    logger.info("📋 [环境变量] 关键配置检查:")
    logger.info(f"   • AI_BUILDER_TOKEN: {'✅ 已配置' if ai_token else '❌ 未配置'}")
    if ai_token:
        logger.info(f"   • Token前缀: {ai_token[:20]}...")
        logger.info(f"   • Token长度: {len(ai_token)}字符")
    logger.info(f"   • SMTP_SERVER: {'✅ 已配置' if smtp_server else '⚠️  未配置（邮件功能将不可用）'}")
    
    # 列出所有环境变量（仅显示AI_BUILDER和SMTP相关的，保护隐私）
    env_vars = {k: v for k, v in os.environ.items() if 'AI_BUILDER' in k or 'SMTP' in k}
    if env_vars:
        logger.info("📋 [环境变量] 相关环境变量:")
        for key in sorted(env_vars.keys()):
            value = env_vars[key]
            if 'TOKEN' in key or 'PASSWORD' in key:
                display_value = f"{value[:20]}..." if len(value) > 20 else "***"
            else:
                display_value = value
            logger.info(f"   • {key}: {display_value}")
    
    logger.info("=" * 80)
    
    # 启动时初始化数据库
    logger.info("📦 [数据库] 正在初始化数据库...")
    try:
        await init_db()
        logger.info("✅ [数据库] 数据库初始化完成")
    except Exception as e:
        logger.error(f"❌ [数据库] 数据库初始化失败: {e}", exc_info=True)
        raise
    
    # 启动价格监控服务（非关键服务，失败不阻止启动）
    logger.info("📊 [价格监控] 正在启动价格监控服务...")
    try:
        await price_monitor.start()
        logger.info("✅ [价格监控] 价格监控服务已启动")
    except Exception as e:
        logger.error(f"❌ [价格监控] 价格监控服务启动失败: {e}", exc_info=True)
        logger.warning("⚠️  [价格监控] 价格监控服务启动失败，但应用将继续运行")
    
    # 启动闹铃监控服务（非关键服务，失败不阻止启动）
    logger.info("🔔 [闹铃监控] 正在启动闹铃监控服务...")
    try:
        await alert_monitor.start()
        logger.info("✅ [闹铃监控] 闹铃监控服务已启动")
    except Exception as e:
        logger.error(f"❌ [闹铃监控] 闹铃监控服务启动失败: {e}", exc_info=True)
        logger.warning("⚠️  [闹铃监控] 闹铃监控服务启动失败，但应用将继续运行")
    
    # 检查AI配置
    logger.info("🤖 [AI配置] 正在检查AI配置...")
    if ai_token:
        logger.info("✅ [AI配置] AI Builder Token已配置 - GPT-5分析功能已启用")
        logger.info(f"🔑 [AI配置] Token前缀: {ai_token[:20]}...")
        logger.info(f"🌐 [AI配置] API端点: https://space.ai-builders.com/backend/v1/chat/completions")
        logger.info(f"🤖 [AI配置] 模型: gpt-5")
    else:
        logger.warning("⚠️  [AI配置] AI_BUILDER_TOKEN未配置 - 将使用基础分析模式")
        logger.warning("💡 [AI配置] 如需启用GPT-5深度分析，请在.env文件中配置AI_BUILDER_TOKEN")
        logger.warning("📖 [AI配置] 详细说明: 查看 AI_SETUP_GUIDE.md")
        logger.warning(f"📄 [AI配置] .env文件路径: {env_file.absolute()}")
    
    logger.info("=" * 80)
    logger.info("✨ [启动完成] 后端服务启动成功！")
    logger.info("📍 [服务信息] API文档: http://localhost:3000/docs")
    logger.info("📍 [服务信息] API地址: http://localhost:3000")
    logger.info("📍 [服务信息] 健康检查: http://localhost:3000/api/health")
    logger.info("=" * 80)
    
    yield
    
    # 关闭时停止服务
    logger.info("🛑 正在停止服务...")
    await alert_monitor.stop()
    await price_monitor.stop()
    logger.info("✅ 服务已关闭")

app = FastAPI(
    title="A股交易管理系统 API",
    description="""
## 📖 API文档说明

这是一个完整的A股个人交易管理系统后端API，提供以下功能：

### 🔐 认证模块
- 用户注册和登录
- JWT Token认证
- 用户信息管理

### 👤 用户模块
- 用户资料查询
- 资金管理
- 资金历史曲线数据

### 📝 交易记录模块
- 按日期查询交易记录
- 创建、更新、删除交易记录
- 完整的交易信息管理

### 💼 持仓模块
- 实时持仓查询
- 止盈止损操作
- 价格提醒设置

### 🤖 AI分析模块
- 交易历史分析
- 胜率统计
- 优化建议生成

## 🚀 快速开始

1. **访问Swagger UI**: http://localhost:3000/docs
2. **访问ReDoc**: http://localhost:3000/redoc
3. **首先注册用户**，然后使用返回的token进行后续API调用

## 🔑 认证说明

大部分API需要JWT Token认证：
1. 调用 `/api/auth/register` 或 `/api/auth/login` 获取token
2. 点击右上角的 **Authorize** 按钮
3. 输入: `Bearer <your_token>` (注意Bearer后面有空格)
4. 点击 **Authorize** 完成认证

## 📝 使用示例

### 注册用户
```json
POST /api/auth/register
{
  "username": "testuser",
  "email": "test@example.com",
  "password": "password123"
}
```

### 登录获取Token
```json
POST /api/auth/login
{
  "username": "testuser",
  "password": "password123"
}
```

返回的token需要在后续请求的Header中使用：
```
Authorization: Bearer <token>
```
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加请求日志中间件（增强版）
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 获取客户端信息
    client_host = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    # 记录请求信息
    logger.info(f"📥 [{timestamp}] {request.method} {request.url.path}")
    logger.debug(f"   • 客户端IP: {client_host}")
    logger.debug(f"   • User-Agent: {user_agent[:50]}...")
    
    # 记录查询参数（如果有）
    if request.url.query:
        logger.debug(f"   • 查询参数: {request.url.query[:100]}...")
    
    # 记录请求体大小（如果是POST/PUT）
    if request.method in ["POST", "PUT", "PATCH"]:
        content_length = request.headers.get("content-length", "0")
        logger.debug(f"   • 请求体大小: {content_length} bytes")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # 状态码分类
        if response.status_code < 200:
            status_emoji = "ℹ️"
        elif response.status_code < 300:
            status_emoji = "✅"
        elif response.status_code < 400:
            status_emoji = "↩️"
        elif response.status_code < 500:
            status_emoji = "⚠️"
        else:
            status_emoji = "❌"
        
        # 记录响应信息
        logger.info(f"📤 [{timestamp}] {status_emoji} {request.method} {request.url.path} - {response.status_code} ({process_time:.3f}s)")
        
        # 记录慢请求（超过1秒）
        if process_time > 1.0:
            logger.warning(f"⏱️  [慢请求] {request.method} {request.url.path} 耗时 {process_time:.3f}s")
        
        # 记录错误详情
        if response.status_code >= 400:
            logger.warning(f"⚠️  [错误] {request.method} {request.url.path} - HTTP {response.status_code}")
        
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"❌ [{timestamp}] 请求处理异常: {request.method} {request.url.path}")
        logger.error(f"❌ [异常] 错误类型: {type(e).__name__}")
        logger.error(f"❌ [异常] 错误详情: {str(e)}")
        logger.error(f"❌ [异常] 耗时: {process_time:.3f}s")
        logger.error("=" * 80, exc_info=True)
        raise

# 注册路由
logger.info("🔗 正在注册API路由...")
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(user.router, prefix="/api/user", tags=["用户"])
app.include_router(trades.router, prefix="/api/trades", tags=["交易记录"])
app.include_router(positions.router, prefix="/api/positions", tags=["持仓"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["AI分析"])
app.include_router(price.router, prefix="/api/price", tags=["价格"])
logger.info("✅ 路由注册完成")

@app.get("/")
async def root():
    logger.info("📋 根路径访问")
    # 如果静态文件存在，返回index.html，否则返回API信息
    # 在Docker容器中，静态文件在/app/static（与main.py同级目录）
    static_dir = Path(__file__).parent / "static"
    index_file = static_dir / "index.html" if static_dir.exists() else None
    if index_file and index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "A股交易管理系统 API", "docs": "/docs"}

# 静态文件服务（用于前端）- 必须在其他路由之后
# 在Docker容器中，静态文件在/app/static（与main.py同级目录）
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    logger.info(f"✅ 静态文件服务已挂载: {static_dir}")
    
    # SPA路由：所有非API请求返回index.html（必须在最后注册）
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # 排除API路径和文档路径
        if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("openapi.json"):
            return {"error": "Not found"}
        
        # 检查是否是静态资源
        static_file = static_dir / full_path
        if static_file.exists() and static_file.is_file():
            return FileResponse(str(static_file))
        
        # 返回index.html（SPA路由）
        index_file = static_dir / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        
        return {"error": "Not found"}
else:
    logger.warning(f"⚠️  静态文件目录不存在: {static_dir}（前端可能未构建）")

@app.get(
    "/api/health",
    summary="健康检查（含环境变量状态）",
    description="""
    健康检查端点，用于监控服务运行状态。
    
    **特点**:
    - 不需要认证即可访问
    - 返回服务状态和基本信息
    - 包含价格监控服务状态
    - 包含环境变量配置状态
    
    **返回信息**:
    - `status`: 服务状态 ("healthy" 或 "unhealthy")
    - `service`: 服务名称
    - `version`: API版本号
    - `price_monitor`: 价格监控服务状态
    - `alert_monitor`: 闹铃监控服务状态
    - `environment`: 环境变量配置状态
    - `timestamp`: 检查时间戳
    """,
    tags=["系统"],
    responses={
        200: {
            "description": "服务健康",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "service": "A股交易管理系统 API",
                        "version": "1.0.0",
                        "price_monitor": "running",
                        "alert_monitor": "running",
                        "environment": {
                            "ai_builder_token": "configured",
                            "smtp_server": "not_configured"
                        },
                        "timestamp": "2026-01-12T11:32:04.231163"
                    }
                }
            }
        }
    }
)
async def health_check():
    """
    健康检查端点（增强版）
    
    用于监控服务状态，返回服务运行状态、环境变量配置和基本信息。
    不需要认证即可访问。
    """
    try:
        # 检查价格监控服务状态
        price_monitor_status = "running" if price_monitor.running else "stopped"
        
        # 检查闹铃监控服务状态
        alert_monitor_status = "running" if alert_monitor.running else "stopped"
        
        # 检查环境变量配置
        ai_token = os.getenv("AI_BUILDER_TOKEN", "")
        smtp_server = os.getenv("SMTP_SERVER", "")
        
        env_status = {
            "ai_builder_token": "configured" if ai_token else "not_configured",
            "smtp_server": "configured" if smtp_server else "not_configured"
        }
        
        # 判断整体健康状态（只要应用能响应请求就认为健康）
        # 监控服务失败不影响基本功能
        is_healthy = True
        
        logger.info(f"🏥 [健康检查] 服务状态检查 - {'健康' if is_healthy else '异常'}")
        logger.info(f"   • 价格监控: {price_monitor_status}")
        logger.info(f"   • 闹铃监控: {alert_monitor_status}")
        logger.info(f"   • AI Token: {env_status['ai_builder_token']}")
        logger.info(f"   • SMTP服务: {env_status['smtp_server']}")
        
        return {
            "status": "healthy" if is_healthy else "degraded",
            "service": "A股交易管理系统 API",
            "version": "1.0.0",
            "price_monitor": price_monitor_status,
            "alert_monitor": alert_monitor_status,
            "environment": env_status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ [健康检查] 健康检查失败: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    # 读取PORT环境变量，默认3000
    port = int(os.getenv("PORT", "3000"))
    logger.info(f"🎯 启动Uvicorn服务器... (端口: {port})")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
