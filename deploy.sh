#!/bin/bash

# 部署脚本
# 使用方法: ./deploy.sh

# 从.env文件加载配置
if [ ! -f .env ]; then
    echo "❌ 错误: .env文件不存在"
    echo "💡 提示: 请先运行 ./setup-env.sh 创建.env文件"
    exit 1
fi

export $(cat .env | grep -v '^#' | xargs)

# 检查必要的环境变量
if [ -z "$DEPLOY_TOKEN" ]; then
    echo "❌ 错误: DEPLOY_TOKEN未设置"
    echo "💡 提示: 请在.env文件中设置DEPLOY_TOKEN"
    exit 1
fi

if [ -z "$GITHUB_REPO_NAME" ]; then
    echo "⚠️  警告: GITHUB_REPO_NAME未设置，使用默认值: trade-view"
    GITHUB_REPO_NAME="trade-view"
fi

TOKEN="$DEPLOY_TOKEN"
SERVICE_NAME="${GITHUB_REPO_NAME}"
BASE_URL="https://space.ai-builders.com/backend/v1"

echo "🚀 开始部署..."
echo ""
echo "📋 部署配置："
echo "   • 服务名: ${SERVICE_NAME}"
echo "   • 仓库: ${GITHUB_REPO_OWNER:-apple-taste}/${GITHUB_REPO_NAME}"
echo "   • 分支: ${GITHUB_BRANCH:-main}"
echo ""

# 检查deploy-config.json是否存在
if [ ! -f deploy-config.json ]; then
    echo "❌ 错误: deploy-config.json文件不存在"
    exit 1
fi

# 提交部署请求
RESPONSE=$(curl -s -X POST "${BASE_URL}/deployments" \
  -H "Accept: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d @deploy-config.json)

# 解析响应
echo "$RESPONSE" | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    print('✅ 部署请求已提交！')
    print(f'服务名: {data.get(\"service_name\", \"N/A\")}')
    print(f'状态: {data.get(\"status\", \"N/A\")}')
    print(f'消息: {data.get(\"message\", \"N/A\")}')
    print('')
    print('⏱️  请等待5-10分钟让部署完成')
    print('💡 可以使用 ./check-deployment.sh 查看部署状态')
except Exception as e:
    print(f'❌ 错误: {e}')
    print('原始响应:')
    print(sys.stdin.read())
"
