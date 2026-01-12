#!/bin/bash

echo "🔍 前端调试监控面板"
echo "===================="
echo ""
echo "📝 实时日志 (Ctrl+C 退出)"
echo "---"

tail -f frontend_dev.log 2>/dev/null | while IFS= read -r line; do
    if [[ $line == *"error"* ]] || [[ $line == *"ERROR"* ]] || [[ $line == *"Error"* ]]; then
        echo -e "\033[31m❌ $line\033[0m"
    elif [[ $line == *"warning"* ]] || [[ $line == *"WARNING"* ]] || [[ $line == *"Warning"* ]]; then
        echo -e "\033[33m⚠️  $line\033[0m"
    elif [[ $line == *"✓"* ]] || [[ $line == *"ready"* ]] || [[ $line == *"Local:"* ]]; then
        echo -e "\033[32m✅ $line\033[0m"
    elif [[ $line == *"localhost"* ]] || [[ $line == *"http"* ]]; then
        echo -e "\033[36m🌐 $line\033[0m"
    else
        echo "$line"
    fi
done
