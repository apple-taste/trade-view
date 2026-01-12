#!/bin/bash

echo "🔍 检查服务运行状态"
echo "=========================================="
echo ""

# 检查后端
echo "📊 后端状态 (端口3000):"
BACKEND_PID=$(lsof -ti:3000 2>/dev/null)
if [ -n "$BACKEND_PID" ]; then
    echo "  ✅ 后端正在运行"
    echo "  📍 PID: $BACKEND_PID"
    echo "  🌐 地址: http://localhost:3000"
    
    # 测试API是否响应
    if curl -s http://localhost:3000/ > /dev/null 2>&1; then
        echo "  ✅ API响应正常"
    else
        echo "  ⚠️  API无响应（可能正在启动）"
    fi
else
    echo "  ❌ 后端未运行"
    echo "  💡 启动命令: cd backend && python3 main.py"
fi

echo ""

# 检查前端
echo "📊 前端状态 (端口5173):"
FRONTEND_PID=$(lsof -ti:5173 2>/dev/null)
if [ -n "$FRONTEND_PID" ]; then
    echo "  ✅ 前端正在运行"
    echo "  📍 PID: $FRONTEND_PID"
    echo "  🌐 地址: http://localhost:5173"
    
    # 测试前端是否响应
    if curl -s http://localhost:5173/ > /dev/null 2>&1; then
        echo "  ✅ 前端响应正常"
    else
        echo "  ⚠️  前端无响应（可能正在启动）"
    fi
else
    echo "  ❌ 前端未运行"
    echo "  💡 启动命令: cd frontend && npm run dev"
fi

echo ""
echo "=========================================="
echo ""

# 检查进程
echo "🔍 检查Python进程:"
PYTHON_PROCESSES=$(ps aux | grep "python.*main.py" | grep -v grep)
if [ -n "$PYTHON_PROCESSES" ]; then
    echo "$PYTHON_PROCESSES" | while read line; do
        echo "  ✅ $line"
    done
else
    echo "  ❌ 未找到后端Python进程"
fi

echo ""

echo "🔍 检查Node进程:"
NODE_PROCESSES=$(ps aux | grep "node.*vite\|npm.*dev" | grep -v grep)
if [ -n "$NODE_PROCESSES" ]; then
    echo "$NODE_PROCESSES" | while read line; do
        echo "  ✅ $line"
    done
else
    echo "  ❌ 未找到前端Node进程"
fi

echo ""
echo "=========================================="
echo "💡 提示: 运行此脚本检查状态: ./check_status.sh"
