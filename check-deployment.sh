#!/bin/bash

# 部署检查和日志查看脚本
# 使用方法: ./check-deployment.sh

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

TOKEN="$DEPLOY_TOKEN"
SERVICE_NAME="${GITHUB_REPO_NAME:-trade-view}"
BASE_URL="https://space.ai-builders.com/backend/v1"

echo "🔍 检查部署状态..."
echo ""

# 1. 检查部署状态
echo "📊 部署状态："
curl -s -X GET "${BASE_URL}/deployments/${SERVICE_NAME}" \
  -H "Accept: application/json" \
  -H "Authorization: Bearer ${TOKEN}" | python3 -c "
import json
import sys
from datetime import datetime
try:
    raw = sys.stdin.read()
    data = json.loads(raw)
    print(f'  服务名: {data.get(\"service_name\", \"N/A\")}')
    print(f'  状态: {data.get(\"status\", \"N/A\")}')
    print(f'  Koyeb状态: {data.get(\"koyeb_status\", \"N/A\")}')
    print(f'  仓库: {data.get(\"repo_url\", \"N/A\")}')
    print(f'  分支: {data.get(\"branch\", \"N/A\")}')
    print(f'  Git提交: {data.get(\"git_commit_id\", \"N/A\")}')
    print(f'  公开URL: {data.get(\"public_url\", \"N/A\")}')
    print(f'  最后部署: {data.get(\"last_deployed_at\", \"N/A\")}')
    print(f'  更新时间: {data.get(\"updated_at\", \"N/A\")}')
    print(f'  消息: {data.get(\"message\", \"N/A\")}')
except json.JSONDecodeError:
    print(f'❌ 错误: 无法解析响应为JSON')
    print(f'  原始响应: {raw[:500]}...')
except Exception as e:
    print(f'❌ 错误: {e}')
"
echo ""

# 2. 检查构建日志
echo "🔨 构建日志（最近30秒）："
curl -s -X GET "${BASE_URL}/deployments/${SERVICE_NAME}/logs?log_type=build&timeout=30" \
  -H "Accept: application/json" \
  -H "Authorization: Bearer ${TOKEN}" | python3 -c "
import json
import sys
try:
    raw = sys.stdin.read()
    data = json.loads(raw)
    logs = data.get('logs', '')
    if logs:
        # 只显示最后1000行
        lines = logs.split('\n')
        if len(lines) > 1000:
            print('  ... (显示最后1000行)')
            print('\n'.join(lines[-1000:]))
        else:
            print(logs)
    else:
        print('  没有构建日志')
except json.JSONDecodeError:
    print(f'❌ 错误: 无法解析响应为JSON')
    print(f'  原始响应: {raw[:200]}...')
except Exception as e:
    print(f'❌ 错误: {e}')
"
echo ""

# 3. 检查运行日志（错误）
echo "🚨 运行错误日志（最近10秒）："
curl -s -X GET "${BASE_URL}/deployments/${SERVICE_NAME}/logs?log_type=runtime&stream=stderr&timeout=10" \
  -H "Accept: application/json" \
  -H "Authorization: Bearer ${TOKEN}" | python3 -c "
import json
import sys
try:
    raw = sys.stdin.read()
    data = json.loads(raw)
    logs = data.get('logs', '')
    if logs:
        # 只显示最后500行
        lines = logs.split('\n')
        if len(lines) > 500:
            print('  ... (显示最后500行)')
            print('\n'.join(lines[-500:]))
        else:
            print(logs)
    else:
        print('  没有错误日志')
except json.JSONDecodeError:
    print(f'❌ 错误: 无法解析响应为JSON')
    print(f'  原始响应: {raw[:200]}...')
except Exception as e:
    print(f'❌ 错误: {e}')
"
echo ""

# 4. 检查网站健康状态
echo "🌐 网站健康检查："
curl -s -I "https://trade-view.ai-builders.space/api/health" | head -5
echo ""

echo "✅ 检查完成！"
