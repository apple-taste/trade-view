#!/bin/bash

echo "📦 使用国内镜像安装依赖（加速下载）"
echo "=========================================="
echo ""

cd "$(dirname "$0")"

# 切换到国内镜像
echo "1️⃣  切换到npm国内镜像..."
npm config set registry https://registry.npmmirror.com
echo "✅ 已切换到: https://registry.npmmirror.com"
echo ""

# 清理旧的依赖
if [ -d "node_modules" ]; then
    echo "2️⃣  清理旧的依赖..."
    rm -rf node_modules package-lock.json
    echo "✅ 清理完成"
    echo ""
fi

# 安装依赖
echo "3️⃣  开始安装依赖..."
echo "这可能需要1-3分钟，请耐心等待..."
echo ""

npm install

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 依赖安装成功！"
    echo ""
    
    # 验证vite是否安装
    if [ -f "node_modules/.bin/vite" ]; then
        echo "✅ vite已正确安装"
        echo ""
        echo "现在可以运行: npm run dev"
    else
        echo "⚠️  vite未找到，可能安装不完整"
    fi
else
    echo ""
    echo "❌ 依赖安装失败！"
    echo ""
    echo "如果网络问题，可以尝试："
    echo "1. 检查网络连接"
    echo "2. 使用VPN或代理"
    echo "3. 稍后重试"
    exit 1
fi
