# 🔍 服务状态检查指南

## 快速检查命令

### 一键检查脚本

```bash
cd /Users/ierx/cursor_workspace/trade-view
./check_status.sh
```

这个脚本会显示：
- ✅ 后端是否运行（端口3000）
- ✅ 前端是否运行（端口5173）
- ✅ 进程ID
- ✅ API响应状态

## 手动检查方法

### 1. 检查端口占用（最准确）

```bash
# 检查后端端口（3000）
lsof -i :3000

# 检查前端端口（5173）
lsof -i :5173

# 如果端口被占用，会显示进程信息
# 如果没有输出，说明服务未运行
```

### 2. 测试API响应

```bash
# 测试后端
curl http://localhost:3000/

# 如果返回JSON，说明后端运行正常
# 如果连接失败，说明后端未运行
```

```bash
# 测试前端
curl http://localhost:5173/

# 如果返回HTML，说明前端运行正常
# 如果连接失败，说明前端未运行
```

### 3. 检查进程

```bash
# 检查后端Python进程
ps aux | grep "python.*main.py" | grep -v grep

# 检查前端Node进程
ps aux | grep "vite\|npm.*dev" | grep -v grep
```

### 4. 检查进程ID

```bash
# 获取后端进程ID
lsof -ti:3000

# 获取前端进程ID
lsof -ti:5173

# 如果有输出，说明服务在运行
# 如果没有输出，说明服务未运行
```

## 状态判断

### ✅ 后端运行中

**特征：**
- `lsof -i :3000` 有输出
- `curl http://localhost:3000/` 返回JSON
- `ps aux | grep "python.*main.py"` 有进程
- 可以访问 http://localhost:3000/docs

**验证：**
```bash
curl http://localhost:3000/ && echo "✅ 后端运行正常"
```

### ❌ 后端未运行

**特征：**
- `lsof -i :3000` 无输出
- `curl http://localhost:3000/` 连接失败
- `ps aux | grep "python.*main.py"` 无进程

**启动：**
```bash
cd backend && python3 main.py
```

### ✅ 前端运行中

**特征：**
- `lsof -i :5173` 有输出
- `curl http://localhost:5173/` 返回HTML
- `ps aux | grep "vite\|npm.*dev"` 有进程
- 浏览器可以访问 http://localhost:5173

**验证：**
```bash
curl http://localhost:5173/ > /dev/null 2>&1 && echo "✅ 前端运行正常" || echo "❌ 前端未运行"
```

### ❌ 前端未运行

**特征：**
- `lsof -i :5173` 无输出
- `curl http://localhost:5173/` 连接失败
- `ps aux | grep "vite\|npm.*dev"` 无进程

**启动：**
```bash
cd frontend && npm run dev
```

## 常用检查命令组合

### 快速检查两个服务

```bash
echo "后端: $(lsof -ti:3000 > /dev/null 2>&1 && echo '✅ 运行中' || echo '❌ 未运行')"
echo "前端: $(lsof -ti:5173 > /dev/null 2>&1 && echo '✅ 运行中' || echo '❌ 未运行')"
```

### 检查并显示详细信息

```bash
# 后端
echo "=== 后端状态 ==="
if lsof -ti:3000 > /dev/null 2>&1; then
    echo "✅ 运行中 (PID: $(lsof -ti:3000))"
    curl -s http://localhost:3000/ | head -1
else
    echo "❌ 未运行"
fi

# 前端
echo ""
echo "=== 前端状态 ==="
if lsof -ti:5173 > /dev/null 2>&1; then
    echo "✅ 运行中 (PID: $(lsof -ti:5173))"
    echo "访问: http://localhost:5173"
else
    echo "❌ 未运行"
fi
```

## 停止服务

### 停止后端

```bash
# 方法1: 通过端口
lsof -ti:3000 | xargs kill -9

# 方法2: 通过进程名
pkill -f "python.*main.py"

# 方法3: 如果知道PID
kill <PID>
```

### 停止前端

```bash
# 方法1: 通过端口
lsof -ti:5173 | xargs kill -9

# 方法2: 在运行前端的终端按 Ctrl+C
```

## 重启服务

### 重启后端

```bash
# 停止


# 启动
cd backend && python3 main.py > backend.log 2>&1 &
```

### 重启前端

```bash
# 停止（在运行前端的终端按 Ctrl+C）
# 然后重新启动
cd frontend && npm run dev
```

## 实时监控脚本

创建一个监控脚本 `monitor.sh`:

```bash
#!/bin/bash
while true; do
    clear
    echo "=== 服务状态监控 ==="
    echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    
    # 后端
    if lsof -ti:3000 > /dev/null 2>&1; then
        echo "后端: ✅ 运行中 (PID: $(lsof -ti:3000))"
    else
        echo "后端: ❌ 未运行"
    fi
    
    # 前端
    if lsof -ti:5173 > /dev/null 2>&1; then
        echo "前端: ✅ 运行中 (PID: $(lsof -ti:5173))"
    else
        echo "前端: ❌ 未运行"
    fi
    
    sleep 2
done
```

使用：
```bash
chmod +x monitor.sh
./monitor.sh
```

## 故障排查

### 端口被占用但不是我们的服务

```bash
# 查看占用端口的进程详情
lsof -i :3000

# 如果发现不是我们的服务，可以强制停止
lsof -ti:3000 | xargs kill -9
```

### 服务启动但无法访问

```bash
# 检查防火墙
# macOS通常不需要配置

# 检查服务是否监听正确地址
netstat -an | grep 3000
netstat -an | grep 5173
```

## 总结

**最简单的检查方法：**

```bash
# 运行检查脚本
./check_status.sh

# 或者手动检查
curl http://localhost:3000/ && echo "后端✅" || echo "后端❌"
curl http://localhost:5173/ && echo "前端✅" || echo "前端❌"
```

现在你可以随时检查服务状态了！🔍
