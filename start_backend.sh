#!/bin/bash
cd "$(dirname "$0")/backend"
echo "🚀 启动后端服务..."
python3 main.py > backend.log 2>&1 &
BACKEND_PID=$!
echo "✅ 后端已启动，PID: $BACKEND_PID"
echo "📋 日志文件: backend/backend.log"
echo "📊 实时查看日志: tail -f backend/backend.log"
echo "🌐 API地址: http://localhost:3000"
echo "📚 API文档: http://localhost:3000/docs"
