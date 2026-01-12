# 后端 API

基于 FastAPI 的 A股交易管理系统后端。

## 技术栈

- FastAPI - 现代、快速的 Web 框架
- SQLAlchemy - ORM
- SQLite - 数据库（开发环境）
- Python-JOSE - JWT 认证
- Passlib - 密码加密
- Pandas - 数据分析（AI分析功能）

## 安装

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

## 运行

```bash
# 开发模式
python main.py

# 或使用 uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 3000
```

## API 文档

启动服务后访问：
- Swagger UI: http://localhost:3000/docs
- ReDoc: http://localhost:3000/redoc

## 环境变量

复制 `.env.example` 为 `.env` 并配置：

```
JWT_SECRET=your-secret-key-change-in-production
DATABASE_URL=sqlite+aiosqlite:///./database.db
```
