#!/bin/bash
echo "🚀 启动A股交易管理系统"
echo "=========================================="
echo ""

# 检查后端
echo "📊 检查后端状态..."
if lsof -ti:3000 > /dev/null 2>&1; then
    echo "✅ 后端已在运行"
else
    echo "⚠️  后端未运行，请先启动后端:"
    echo "   cd backend && python3 main.py"
    echo ""
fi

# 检查前端
echo "📊 检查前端状态..."
if lsof -ti:5173 > /dev/null 2>&1; then
    echo "✅ 前端已在运行"
else
    echo "🚀 启动前端..."
    cd frontend
    ./start_frontend.sh
fi
