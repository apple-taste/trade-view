# A股个人交易管理系统

一个功能完整的A股个人交易管理应用，支持交易记录、持仓管理、实时价格监控和AI分析。

## 功能特性

- 🔐 用户注册和登录
- 👤 用户面板：资金管理和资金曲线展示
- 📅 日历面板：按日期查看交易记录
- 📝 开仓记录历史：完整的交易记录管理
- 💼 持仓面板：实时价格监控、止盈止损管理
- 🤖 AI分析：交易历史分析和优化建议

## 技术栈

### 前端
- React 18 + TypeScript
- Vite
- Tailwind CSS
- React Router
- Recharts (资金曲线)
- Socket.io Client (实时价格)

### 后端
- FastAPI (Python)
- SQLAlchemy + SQLite (开发) / PostgreSQL (生产)
- JWT 认证
- Pandas (数据分析)
- WebSocket (实时价格推送)

## 快速开始

### 安装依赖

**前端:**
```bash
cd frontend && npm install
```

**后端:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 开发模式

**方式一：分别启动**
```bash
# 终端1 - 启动后端
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
python main.py

# 终端2 - 启动前端
cd frontend
npm run dev
```

**方式二：使用npm脚本（需要先安装前端依赖）**
```bash
npm run dev
```

前端运行在 http://localhost:5173
后端运行在 http://localhost:3000

**API文档:**
- **Swagger UI**: http://localhost:3000/docs (交互式API文档，可直接测试)
- **ReDoc**: http://localhost:3000/redoc (另一种文档格式)
- **详细使用指南**: 查看 `SWAGGER_UI_GUIDE.md`

### 构建生产版本
```bash
npm run build
```

## 📚 文档

- **README.md**: 项目说明（本文件）
- **SWAGGER_UI_GUIDE.md**: Swagger UI 详细使用指南
- **DEBUG_GUIDE.md**: 日志调试指南
- **backend/README.md**: 后端API说明

## 项目结构

```
trade-view/
├── frontend/          # React前端应用
├── backend/           # FastAPI后端API
│   ├── app/           # 应用代码
│   │   ├── routers/   # API路由
│   │   ├── models.py  # Pydantic模型
│   │   ├── database.py # 数据库模型
│   │   └── middleware/ # 中间件
│   └── main.py        # 入口文件
└── README.md
```
