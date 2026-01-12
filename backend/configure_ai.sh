#!/bin/bash

# AI配置脚本

echo "================================"
echo "🤖 AI深度分析配置脚本"
echo "================================"
echo ""

# 检查是否已存在.env文件
if [ -f ".env" ]; then
    echo "⚠️  检测到已存在 .env 文件"
    read -p "是否覆盖现有配置? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ 配置已取消"
        exit 0
    fi
fi

# 创建.env文件
cat > .env << 'EOF'
# ================================
# AI Builder Space 配置
# ================================
# ChatGPT-5 API Token（通过AI Builder Space中转）
AI_BUILDER_TOKEN=sk_cb7877e7_e4382f5e748e92cdd707b6f937e8cc8a5c2a

# ================================
# 邮箱服务配置（可选）
# ================================
# SMTP_SERVER=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USERNAME=your_email@gmail.com
# SMTP_PASSWORD=your_gmail_app_password
# SMTP_FROM_EMAIL=your_email@gmail.com
# SMTP_FROM_NAME=Trade View 交易提醒
EOF

echo "✅ .env 文件已创建"
echo ""
echo "📝 配置内容："
echo "   AI_BUILDER_TOKEN: sk_cb7877e7_..."
echo ""
echo "🚀 下一步："
echo "   1. 重启后端服务: python3 main.py"
echo "   2. 查看启动日志确认AI配置"
echo "   3. 点击 '🤖 获取AI深度分析' 测试"
echo ""
echo "================================"
