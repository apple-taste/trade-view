from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta

from app.database import get_db, User, CapitalHistory
from app.models import UserRegister, UserLogin, TokenResponse, UserResponse
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
# 使用pbkdf2_sha256作为密码加密方案（更兼容，无bcrypt版本问题）
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
ALGORITHM = "HS256"

def create_access_token(user_id: int, is_admin: bool = False) -> str:
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode = {"userId": user_id, "isAdmin": is_admin, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="用户注册",
    description="""
    注册新用户账号
    
    - **username**: 用户名，3-20个字符，唯一
    - **email**: 邮箱地址，唯一，用于登录
    - **password**: 密码，建议至少8位
    
    注册成功后会：
    1. 创建用户账号
    2. 初始化资金为10万元
    3. 返回JWT Token用于后续API调用
    """,
    responses={
        201: {
            "description": "注册成功",
            "content": {
                "application/json": {
                    "example": {
                        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "user": {
                            "id": 1,
                            "username": "trader001",
                            "email": "trader@example.com",
                            "created_at": "2024-01-11T10:00:00"
                        }
                    }
                }
            }
        },
        400: {"description": "用户名或邮箱已存在"}
    }
)
async def register(user_data: UserRegister, db: AsyncSession = Depends(get_db)):
    logger.info(f"🔐 [注册] 用户名: {user_data.username}, 邮箱: {user_data.email}")
    
    # 调试：检查数据库中是否有用户
    all_users_result = await db.execute(select(User))
    all_users = all_users_result.scalars().all()
    logger.info(f"📊 [注册调试] 数据库中用户总数: {len(all_users)}")
    
    # 检查用户是否已存在
    result = await db.execute(
        select(User).where((User.username == user_data.username) | (User.email == user_data.email))
    )
    existing_user = result.scalar_one_or_none()
    if existing_user:
        logger.warning(f"❌ [注册失败] 用户名或邮箱已存在: {user_data.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名或邮箱已存在"
        )
    
    # 创建用户
    password_hash = pwd_context.hash(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=password_hash
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # 初始化资金历史
    initial_capital = 100000  # 默认10万
    capital_history = CapitalHistory(
        user_id=new_user.id,
        date=datetime.utcnow().date(),
        capital=initial_capital
    )
    db.add(capital_history)
    await db.commit()
    
    # 生成token
    token = create_access_token(new_user.id, bool(getattr(new_user, "is_admin", False)))
    
    logger.info(f"✅ [注册成功] 用户ID: {new_user.id}, 用户名: {new_user.username}")
    
    return TokenResponse(
        token=token,
        user=UserResponse(
            id=new_user.id,
            username=new_user.username,
            email=new_user.email,
            created_at=new_user.created_at
        )
    )

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="用户登录",
    description="""
    用户登录获取JWT Token
    
    - **username**: 可以使用用户名或邮箱登录
    - **password**: 用户密码
    
    登录成功后返回Token，需要在后续请求的Header中添加：
    ```
    Authorization: Bearer <token>
    ```
    
    Token有效期为7天
    """,
    responses={
        200: {
            "description": "登录成功",
            "content": {
                "application/json": {
                    "example": {
                        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "user": {
                            "id": 1,
                            "username": "trader001",
                            "email": "trader@example.com",
                            "created_at": "2024-01-11T10:00:00"
                        }
                    }
                }
            }
        },
        401: {"description": "用户名或密码错误"}
    }
)
async def login(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    logger.info(f"🔑 [登录] 用户名: {user_data.username}")
    
    # 查找用户
    result = await db.execute(
        select(User).where((User.username == user_data.username) | (User.email == user_data.username))
    )
    user = result.scalar_one_or_none()
    
    # 调试：检查数据库中是否有用户
    all_users_result = await db.execute(select(User))
    all_users = all_users_result.scalars().all()
    logger.info(f"📊 [登录调试] 数据库中用户总数: {len(all_users)}")
    if all_users:
        logger.info(f"📊 [登录调试] 用户列表: {[u.username for u in all_users]}")
    
    if not user:
        logger.warning(f"❌ [登录失败] 用户不存在: {user_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    if not pwd_context.verify(user_data.password, user.password_hash):
        logger.warning(f"❌ [登录失败] 密码错误: {user_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    user.last_login_at = datetime.utcnow()
    await db.commit()

    # 生成token
    token = create_access_token(user.id, bool(getattr(user, "is_admin", False)))
    
    logger.info(f"✅ [登录成功] 用户ID: {user.id}, 用户名: {user.username}")
    
    return TokenResponse(
        token=token,
        user=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            created_at=user.created_at
        )
    )
