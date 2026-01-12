#!/bin/bash

echo "🚀 启动前端服务"
echo "=========================================="

cd "$(dirname "$0")"

# 检查依赖是否已安装
if [ ! -f "node_modules/.bin/vite" ]; then
    echo "📦 检测到依赖未安装，开始安装..."
    echo "这可能需要几分钟时间，请耐心等待..."
    echo ""
    
    npm install
    
    if [ $? -ne 0 ]; then
        echo ""
        echo "❌ 依赖安装失败！"
        echo "请检查错误信息并重试"
        exit 1
    fi
    
    echo ""
    echo "✅ 依赖安装完成！"
    echo ""
fi

# 检查端口是否被占用
if lsof -ti:5173 > /dev/null 2>&1; then
    echo "⚠️  端口5173已被占用"
    echo "正在停止占用端口的进程..."
    lsof -ti:5173 | xargs kill -9 2>/dev/null
    sleep 1
fi

# 启动前端
echo "🚀 启动前端开发服务器..."
echo "前端将在 http://localhost:5173 启动"
echo ""
echo "按 Ctrl+C 停止服务"
echo "=========================================="
echo ""

npm run dev
