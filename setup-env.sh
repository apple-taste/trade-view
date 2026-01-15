#!/bin/bash

# 设置环境变量脚本
# 使用方法: ./setup-env.sh

echo "🔧 设置环境变量..."
echo ""

# 检查.env文件是否已存在
if [ -f .env ]; then
    echo "⚠️  .env文件已存在"
    read -p "是否要覆盖现有配置？(y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ 已取消"
        exit 1
    fi
fi

# 从用户输入获取配置
echo "📝 请输入以下配置信息："
echo ""

# GitHub Token
read -p "GitHub Personal Access Token: " GITHUB_TOKEN
if [ -z "$GITHUB_TOKEN" ]; then
    echo "⚠️  警告: GitHub Token为空，将使用默认值"
    GITHUB_TOKEN="your_github_token_here"
fi

# Deploy Token
read -p "AI Builder Space Deploy Token: " DEPLOY_TOKEN
if [ -z "$DEPLOY_TOKEN" ]; then
    echo "⚠️  警告: Deploy Token为空，将使用默认值"
    DEPLOY_TOKEN="your_deploy_token_here"
fi

# GitHub仓库信息
read -p "GitHub仓库所有者 (默认: apple-taste): " GITHUB_REPO_OWNER
GITHUB_REPO_OWNER=${GITHUB_REPO_OWNER:-apple-taste}

read -p "GitHub仓库名称 (默认: trade-view): " GITHUB_REPO_NAME
GITHUB_REPO_NAME=${GITHUB_REPO_NAME:-trade-view}

read -p "GitHub分支 (默认: main): " GITHUB_BRANCH
GITHUB_BRANCH=${GITHUB_BRANCH:-main}

# 数据库配置
read -p "数据库URL (PostgreSQL): " DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
    echo "⚠️  警告: 数据库URL为空"
    DATABASE_URL="postgresql://postgres:password@host:5432/postgres"
fi

# JWT Secret
read -p "JWT密钥 (留空自动生成): " JWT_SECRET
if [ -z "$JWT_SECRET" ]; then
    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || echo "your_jwt_secret_here")
    echo "✅ 已自动生成JWT密钥"
fi

# AI Builder Token
read -p "AI Builder Token: " AI_BUILDER_TOKEN
if [ -z "$AI_BUILDER_TOKEN" ]; then
    AI_BUILDER_TOKEN="your_ai_builder_token_here"
fi

# 创建.env文件
cat > .env << EOF
# ============================================
# GitHub 和部署配置
# ============================================

# GitHub Personal Access Token (用于git push)
# 获取方式：https://github.com/settings/tokens/new
GITHUB_TOKEN=${GITHUB_TOKEN}

# AI Builder Space Deployment Token (用于部署到Koyeb)
# 获取方式：https://space.ai-builders.com/
DEPLOY_TOKEN=${DEPLOY_TOKEN}

# GitHub仓库信息
GITHUB_REPO_OWNER=${GITHUB_REPO_OWNER}
GITHUB_REPO_NAME=${GITHUB_REPO_NAME}
GITHUB_BRANCH=${GITHUB_BRANCH}

# ============================================
# 后端环境变量
# ============================================

# 数据库配置
DATABASE_URL=${DATABASE_URL}

# JWT密钥（用于生成和验证JWT token）
JWT_SECRET=${JWT_SECRET}

# ChatGPT-5 API Token（通过AI Builder Space中转）
AI_BUILDER_TOKEN=${AI_BUILDER_TOKEN}

# 日志级别
LOG_LEVEL=info

# 环境
NODE_ENV=production
EOF

echo ""
echo "✅ .env文件已创建！"
echo ""
echo "📋 配置摘要："
echo "   • GitHub仓库: ${GITHUB_REPO_OWNER}/${GITHUB_REPO_NAME}"
echo "   • GitHub分支: ${GITHUB_BRANCH}"
echo "   • GitHub Token: ${GITHUB_TOKEN:0:10}..."
echo "   • Deploy Token: ${DEPLOY_TOKEN:0:10}..."
echo "   • JWT Secret: ${JWT_SECRET:0:10}..."
echo ""
echo "💡 提示: .env文件已添加到.gitignore，不会被提交到GitHub"
