#!/bin/bash

echo "📦 开始安装前端依赖..."
echo "这可能需要几分钟时间，请耐心等待..."
echo ""

cd "$(dirname "$0")"

# 清理旧的依赖（如果有问题）
if [ -d "node_modules" ]; then
    echo "清理旧的node_modules..."
    rm -rf node_modules
fi

if [ -f "package-lock.json" ]; then
    echo "清理旧的package-lock.json..."
    rm -f package-lock.json
fi

echo ""
echo "开始安装依赖..."
npm install

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 依赖安装成功！"
    echo "现在可以运行: npm run dev"
else
    echo ""
    echo "❌ 依赖安装失败，请检查错误信息"
    exit 1
fi
