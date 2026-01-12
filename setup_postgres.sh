#!/bin/bash
# PostgreSQL快速设置脚本

echo "================================================================================
🚀 PostgreSQL数据库设置向导
================================================================================
"

echo "📋 请按照以下步骤操作："
echo ""
echo "1. 访问 https://supabase.com/ 创建账号"
echo "2. 创建新项目（Name: trade-view）"
echo "3. 设置数据库密码（请保存！）"
echo "4. 等待项目创建完成（2-3分钟）"
echo "5. 在Settings → Database → Connection string → URI 复制连接字符串"
echo ""
read -p "按Enter继续，或Ctrl+C取消..."

echo ""
echo "请粘贴你的PostgreSQL连接字符串："
echo "格式：postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres"
read -p "DATABASE_URL: " DATABASE_URL

if [ -z "$DATABASE_URL" ]; then
    echo "❌ 错误：连接字符串不能为空"
    exit 1
fi

# 更新deploy-config.json
echo ""
echo "📝 更新 deploy-config.json..."
python3 << PYTHON_SCRIPT
import json
import sys

try:
    with open('deploy-config.json', 'r') as f:
        config = json.load(f)
    
    config['env_vars']['DATABASE_URL'] = sys.argv[1]
    
    with open('deploy-config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print("✅ deploy-config.json 已更新")
    print(f"✅ DATABASE_URL 已设置: {sys.argv[1].split('@')[0]}@***")
except Exception as e:
    print(f"❌ 错误: {e}")
    sys.exit(1)
PYTHON_SCRIPT "$DATABASE_URL"

if [ $? -eq 0 ]; then
    echo ""
    echo "================================================================================
✅ 配置完成！
================================================================================
"
    echo "下一步："
    echo "1. 提交代码: git add deploy-config.json && git commit -m 'Add PostgreSQL config' && git push"
    echo "2. 重新部署应用"
    echo ""
    echo "部署命令："
    echo "TOKEN=\"sk_cb7877e7_e4382f5e748e92cdd707b6f937e8cc8a5c2a\""
    echo "curl -X POST \"https://space.ai-builders.com/backend/v1/deployments\" \\"
    echo "  -H \"Accept: application/json\" \\"
    echo "  -H \"Authorization: Bearer \$TOKEN\" \\"
    echo "  -H \"Content-Type: application/json\" \\"
    echo "  -d @deploy-config.json"
else
    echo "❌ 配置失败，请手动编辑 deploy-config.json"
fi
