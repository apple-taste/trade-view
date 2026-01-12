#!/bin/bash
cd "$(dirname "$0")/frontend"
echo "🚀 启动前端服务..."
if [ ! -d "node_modules" ]; then
    echo "📦 安装依赖..."
    npm install
fi
npm run dev
