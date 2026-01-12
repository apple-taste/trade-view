#!/bin/bash
echo "🔍 快速检查服务状态"
echo ""

# 检查后端
BACKEND=$(lsof -ti:3000 2>/dev/null)
if [ -n "$BACKEND" ]; then
    echo "✅ 后端运行中 (PID: $BACKEND)"
    curl -s http://localhost:3000/ > /dev/null 2>&1 && echo "   API响应正常" || echo "   ⚠️  API无响应"
else
    echo "❌ 后端未运行"
fi

# 检查前端
FRONTEND=$(lsof -ti:5173 2>/dev/null)
if [ -n "$FRONTEND" ]; then
    echo "✅ 前端运行中 (PID: $FRONTEND)"
else
    echo "❌ 前端未运行"
fi
