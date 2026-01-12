#!/bin/bash

echo "🔍 检查npm install状态和网络问题"
echo "=========================================="
echo ""

cd "$(dirname "$0")"

# 1. 检查npm install进程
echo "1️⃣  检查npm install进程:"
NPM_PID=$(pgrep -f "npm install" | head -1)
if [ -n "$NPM_PID" ]; then
    echo "  ✅ npm install进程存在 (PID: $NPM_PID)"
    echo "  运行时间: $(ps -p $NPM_PID -o etime= 2>/dev/null | xargs)"
    echo "  CPU使用: $(ps -p $NPM_PID -o %cpu= 2>/dev/null | xargs)%"
    echo "  内存使用: $(ps -p $NPM_PID -o rss= 2>/dev/null | xargs | awk '{printf "%.1f MB\n", $1/1024}')"
else
    echo "  ❌ 未找到npm install进程"
fi

echo ""

# 2. 检查node_modules进度
echo "2️⃣  检查安装进度:"
if [ -d "node_modules" ]; then
    PACKAGE_COUNT=$(ls node_modules 2>/dev/null | wc -l | xargs)
    echo "  ✅ node_modules目录存在"
    echo "  已安装包数量: $PACKAGE_COUNT"
    
    if [ -f "node_modules/.bin/vite" ]; then
        echo "  ✅ vite已安装"
    else
        echo "  ⏳ vite还未安装"
    fi
else
    echo "  ❌ node_modules目录不存在"
fi

echo ""

# 3. 检查网络连接
echo "3️⃣  检查网络连接:"
echo "  测试npm registry连接..."
if timeout 3 curl -s https://registry.npmjs.org/ > /dev/null 2>&1; then
    echo "  ✅ npm registry连接正常"
else
    echo "  ❌ npm registry连接失败（可能网络慢或需要代理）"
fi

echo ""

# 4. 检查npm配置
echo "4️⃣  npm配置:"
echo "  Registry: $(npm config get registry)"
echo "  代理设置: $(npm config get proxy || echo '无')"
echo "  HTTP代理: $(npm config get https-proxy || echo '无')"

echo ""

# 5. 检查npm日志
echo "5️⃣  检查npm错误日志:"
LOG_FILE=$(ls -t ~/.npm/_logs/*-debug-*.log 2>/dev/null | head -1)
if [ -n "$LOG_FILE" ] && [ -f "$LOG_FILE" ]; then
    echo "  最新日志: $LOG_FILE"
    ERROR_COUNT=$(grep -i "error\|failed\|timeout" "$LOG_FILE" 2>/dev/null | wc -l | xargs)
    if [ "$ERROR_COUNT" -gt 0 ]; then
        echo "  ⚠️  发现 $ERROR_COUNT 个错误/警告"
        echo "  最近的错误:"
        grep -i "error\|failed\|timeout" "$LOG_FILE" 2>/dev/null | tail -3 | sed 's/^/    /'
    else
        echo "  ✅ 未发现明显错误"
    fi
else
    echo "  ℹ️  未找到日志文件"
fi

echo ""

# 6. 建议
echo "6️⃣  建议:"
if [ -n "$NPM_PID" ]; then
    RUNTIME=$(ps -p $NPM_PID -o etime= 2>/dev/null | xargs)
    echo "  npm install已运行: $RUNTIME"
    
    if [ ! -d "node_modules" ] || [ ! -f "node_modules/.bin/vite" ]; then
        echo "  ⚠️  如果运行超过5分钟仍未完成，建议："
        echo "    1. 停止当前进程: kill $NPM_PID"
        echo "    2. 使用国内镜像: npm config set registry https://registry.npmmirror.com"
        echo "    3. 重新安装: npm install"
    fi
else
    echo "  npm install未运行，可以开始安装"
fi

echo ""
echo "=========================================="
