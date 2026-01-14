#!/bin/bash
# GitHub仓库创建和代码推送脚本

set -e

REPO_NAME="trade-view"
REPO_OWNER="apple-taste"
REPO_DESC="A股交易管理系统 - A股个人交易管理应用，支持交易记录、持仓管理、实时价格监控和AI分析"

echo "=================================================================================="
echo "🚀 GitHub仓库创建和代码推送脚本"
echo "=================================================================================="
echo ""

# 检查是否已提供token
if [ -z "$1" ]; then
    echo "📋 使用方法："
    echo "  ./setup_github.sh <YOUR_PERSONAL_ACCESS_TOKEN>"
    echo ""
    echo "🔑 如何获取Personal Access Token："
    echo "  1. 访问：https://github.com/settings/tokens/new"
    echo "  2. 点击 'Generate new token (classic)'"
    echo "  3. 选择权限：勾选 'repo' (全部权限)"
    echo "  4. 点击 'Generate token'"
    echo "  5. 复制生成的token"
    echo ""
    echo "💡 然后运行："
    echo "  ./setup_github.sh YOUR_TOKEN_HERE"
    echo ""
    exit 1
fi

TOKEN="$1"

echo "✅ Token已提供"
echo ""

# 检查仓库是否已存在
echo "🔍 检查仓库是否存在..."
if curl -s -H "Authorization: token $TOKEN" "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME" | grep -q '"id"'; then
    echo "✅ 仓库已存在：https://github.com/$REPO_OWNER/$REPO_NAME"
else
    echo "📦 正在创建仓库..."
    RESPONSE=$(curl -s -X POST \
        -H "Accept: application/vnd.github.v3+json" \
        -H "Authorization: token $TOKEN" \
        "https://api.github.com/user/repos" \
        -d "{
            \"name\": \"$REPO_NAME\",
            \"description\": \"$REPO_DESC\",
            \"private\": false
        }")
    
    if echo "$RESPONSE" | grep -q '"id"'; then
        echo "✅ 仓库创建成功！"
        echo "   URL: https://github.com/$REPO_OWNER/$REPO_NAME"
    else
        echo "❌ 仓库创建失败："
        echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
        exit 1
    fi
fi

echo ""
echo "🔧 配置Git remote..."
git init
git add .
git commit -m "Update for deployment" 2>/dev/null || echo "Nothing to commit"
git branch -M main
git remote remove origin 2>/dev/null || true
git remote add origin "https://${TOKEN}@github.com/$REPO_OWNER/$REPO_NAME.git"

echo "✅ Git remote已配置"
echo ""

echo "📤 正在推送代码..."
git push -u origin main

echo ""
echo "=================================================================================="
echo "🚀 开始部署流程"
echo "=================================================================================="

if [ -f "./deploy.sh" ]; then
    echo "� 检测到 deploy.sh，正在执行部署..."
    chmod +x ./deploy.sh
    ./deploy.sh
else
    echo "⚠️ 未找到 deploy.sh，跳过自动部署。"
    echo "请手动运行部署命令或检查 deploy.sh 文件是否存在。"
fi

echo ""
echo "=================================================================================="
echo "✅ 所有操作完成！"
echo "=================================================================================="
