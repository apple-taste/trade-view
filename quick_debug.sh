#!/bin/bash

echo "🚀 快速调试工具"
echo "================"
echo ""
echo "选择操作:"
echo "1) 查看前端日志"
echo "2) 查看后端日志"
echo "3) 检查端口占用"
echo "4) 检查进程状态"
echo "5) 重启前端"
echo "6) 实时监控前端日志"
echo ""
read -p "请选择 (1-6): " choice

case $choice in
    1)
        echo "📝 前端日志 (最后50行):"
        tail -n 50 frontend_dev.log 2>/dev/null || echo "日志文件不存在"
        ;;
    2)
        echo "📝 后端日志 (最后50行):"
        tail -n 50 backend/backend.log 2>/dev/null || echo "日志文件不存在"
        ;;
    3)
        echo "🔍 检查端口占用:"
        echo "端口 5173 (前端):"
        lsof -i :5173 2>/dev/null || echo "  未占用"
        echo "端口 3000 (后端):"
        lsof -i :3000 2>/dev/null || echo "  未占用"
        ;;
    4)
        echo "🔍 检查进程状态:"
        echo "前端进程:"
        ps aux | grep -E "vite|node.*dev" | grep -v grep || echo "  未运行"
        echo "后端进程:"
        ps aux | grep -E "uvicorn|python.*main.py" | grep -v grep || echo "  未运行"
        ;;
    5)
        echo "🔄 重启前端..."
        pkill -f "vite" 2>/dev/null
        sleep 2
        cd frontend && npm run dev > ../frontend_dev.log 2>&1 &
        echo "✅ 前端已重启，PID: $!"
        echo "查看日志: tail -f frontend_dev.log"
        ;;
    6)
        echo "📊 实时监控前端日志 (Ctrl+C 退出):"
        ./monitor_frontend.sh
        ;;
    *)
        echo "无效选择"
        ;;
esac
