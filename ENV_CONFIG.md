# 环境变量配置指南

本项目使用 `.env` 文件管理敏感配置信息（token、密码等）。

## 📋 快速开始

### 1. 创建 `.env` 文件

**方法一：使用设置脚本（推荐）**
```bash
./setup-env.sh
```

**方法二：手动创建**
```bash
# 复制模板（如果存在）
cp .env.example .env

# 编辑 .env 文件，填入你的配置
nano .env  # 或使用其他编辑器
```

### 2. 配置说明

`.env` 文件包含以下配置项：

#### GitHub 和部署配置

```bash
# GitHub Personal Access Token (用于git push)
# 获取方式：https://github.com/settings/tokens/new
# 需要权限：repo (Full control of private repositories)
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# AI Builder Space Deployment Token (用于部署到Koyeb)
# 获取方式：https://space.ai-builders.com/
DEPLOY_TOKEN=sk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# GitHub仓库信息
GITHUB_REPO_OWNER=apple-taste
GITHUB_REPO_NAME=trade-view
GITHUB_BRANCH=main
```

#### 后端环境变量

```bash
# 数据库配置（PostgreSQL）
DATABASE_URL=postgresql://postgres:password@host:5432/postgres

# JWT密钥（用于生成和验证JWT token）
# 可以使用以下命令生成：python3 -c "import secrets; print(secrets.token_urlsafe(32))"
JWT_SECRET=your_jwt_secret_here

# ChatGPT-5 API Token（通过AI Builder Space中转）
AI_BUILDER_TOKEN=sk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 日志级别
LOG_LEVEL=info

# 环境
NODE_ENV=production
```

## 🔧 使用方法

### 查看部署状态
```bash
./check-deployment.sh
```

### 部署应用
```bash
./deploy.sh
```

### 重新设置环境变量
```bash
./setup-env.sh
```

## 🔒 安全说明

1. **`.env` 文件已在 `.gitignore` 中**
   - 不会被提交到 GitHub
   - 请勿手动将 `.env` 添加到 git

2. **敏感信息保护**
   - 所有 token 和密码都存储在 `.env` 文件中
   - 不要将 `.env` 文件分享给他人
   - 不要在代码中硬编码 token

3. **团队协作**
   - 使用 `.env.example` 作为模板（不包含真实值）
   - 团队成员各自创建自己的 `.env` 文件

## 📝 获取 Token

### GitHub Personal Access Token

1. 访问：https://github.com/settings/tokens/new
2. 点击 "Generate new token (classic)"
3. 设置名称和过期时间
4. 选择权限：`repo` (Full control of private repositories)
5. 点击 "Generate token"
6. 复制生成的 token（只显示一次）

### AI Builder Space Deployment Token

1. 访问：https://space.ai-builders.com/
2. 登录你的账户
3. 在设置中找到 API Token
4. 复制 token

## ✅ 验证配置

运行以下命令验证配置是否正确：

```bash
# 检查.env文件是否存在
ls -la .env

# 检查环境变量是否加载
source .env && echo "GITHUB_TOKEN: ${GITHUB_TOKEN:0:10}..."
```

## 🐛 常见问题

### Q: `.env` 文件不存在怎么办？
A: 运行 `./setup-env.sh` 创建配置文件

### Q: 如何更新 token？
A: 直接编辑 `.env` 文件，或运行 `./setup-env.sh` 重新设置

### Q: `.env` 文件会被提交到 GitHub 吗？
A: 不会，`.env` 已在 `.gitignore` 中

### Q: 部署时提示 token 错误？
A: 检查 `.env` 文件中的 `DEPLOY_TOKEN` 是否正确设置
