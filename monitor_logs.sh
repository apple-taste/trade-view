#!/bin/bash
cd "$(dirname "$0")/backend"
echo "📊 监控后端日志（按 Ctrl+C 退出）..."
echo "=========================================="
tail -f backend.log
