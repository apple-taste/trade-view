# 🐛 前端可视化调试指南

## 📋 目录
1. [快速启动](#快速启动)
2. [调试工具](#调试工具)
3. [常见问题排查](#常见问题排查)
4. [实时日志监控](#实时日志监控)
5. [浏览器调试技巧](#浏览器调试技巧)
6. [性能分析](#性能分析)

---

## 🚀 快速启动

### 1. 启动前端开发服务器

```bash
# 方式1: 使用npm脚本（推荐）
cd frontend
npm run dev

# 方式2: 后台运行并查看日志
cd frontend
npm run dev > ../frontend_dev.log 2>&1 &
tail -f ../frontend_dev.log
```

### 2. 访问应用

- **前端地址**: http://localhost:5173
- **后端API**: http://localhost:3000
- **Swagger UI**: http://localhost:3000/docs

---

## 🔧 调试工具

### A. 终端日志监控

#### 实时查看前端日志
```bash
# 查看实时日志
tail -f frontend_dev.log

# 查看最后50行日志
tail -n 50 frontend_dev.log

# 搜索错误
grep -i error frontend_dev.log
grep -i warning frontend_dev.log
```

#### 查看构建信息
```bash
# 查看Vite构建信息
cd frontend
npm run build 2>&1 | tee ../build.log

# 查看依赖树
npm list --depth=0
```

### B. 浏览器开发者工具

#### 1. 打开开发者工具
- **Chrome/Edge**: `F12` 或 `Cmd+Option+I` (Mac) / `Ctrl+Shift+I` (Windows)
- **Firefox**: `F12` 或 `Cmd+Option+I` (Mac) / `Ctrl+Shift+I` (Windows)
- **Safari**: `Cmd+Option+I` (需先启用开发者菜单)

#### 2. 关键面板

##### Console（控制台）
```
📍 位置: 开发者工具 → Console 标签

功能:
- 查看 JavaScript 错误和警告
- 执行调试命令
- 查看 console.log() 输出
- 检查网络请求错误

常用命令:
console.log('调试信息', data)
console.error('错误信息', error)
console.warn('警告信息', warning)
console.table(array)  // 表格形式显示数组
```

##### Network（网络）
```
📍 位置: 开发者工具 → Network 标签

功能:
- 监控所有HTTP请求
- 查看API响应
- 检查请求/响应头
- 分析请求耗时

过滤设置:
- XHR/Fetch: 只看API请求
- JS: 只看JavaScript文件
- CSS: 只看样式文件
```

##### Sources（源代码）
```
📍 位置: 开发者工具 → Sources 标签

功能:
- 设置断点
- 单步调试
- 查看变量值
- 修改代码实时测试

调试步骤:
1. 找到要调试的文件
2. 点击行号设置断点
3. 刷新页面触发断点
4. 使用调试控制按钮:
   - ▶️ Resume: 继续执行
   - ⏸️ Step over: 跳过当前函数
   - ⬇️ Step into: 进入函数内部
   - ⬆️ Step out: 跳出当前函数
```

##### React DevTools（React专用）
```
安装: Chrome扩展商店搜索 "React Developer Tools"

功能:
- 查看组件树
- 检查组件props和state
- 性能分析
- 组件高亮显示
```

---

## 🔍 常见问题排查

### 1. 页面白屏/无法加载

#### 检查清单:
```bash
# ✅ 步骤1: 检查前端服务器是否运行
curl http://localhost:5173

# ✅ 步骤2: 检查端口是否被占用
lsof -i :5173

# ✅ 步骤3: 查看浏览器控制台错误
# 打开浏览器 → F12 → Console标签

# ✅ 步骤4: 检查网络请求
# 打开浏览器 → F12 → Network标签 → 刷新页面
```

#### 常见错误:

**错误1: `Failed to fetch`**
```
原因: 后端API未启动或CORS配置问题
解决: 
1. 检查后端是否运行: curl http://localhost:3000/api/health
2. 检查vite.config.ts中的proxy配置
```

**错误2: `Cannot find module`**
```
原因: 依赖未安装或路径错误
解决:
cd frontend
rm -rf node_modules package-lock.json
npm install
```

**错误3: `Port 5173 is already in use`**
```
原因: 端口被占用
解决:
# 查找占用进程
lsof -i :5173
# 杀死进程
kill -9 <PID>
# 或使用其他端口
npm run dev -- --port 5174
```

### 2. API请求失败

#### 调试步骤:
```javascript
// 1. 在浏览器Console中测试API
fetch('http://localhost:3000/api/user/profile', {
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('token')}`
  }
})
.then(r => r.json())
.then(console.log)
.catch(console.error)

// 2. 检查Network面板
// - 查看请求状态码
// - 查看请求/响应头
// - 查看响应内容
```

#### 常见状态码:
- `401 Unauthorized`: Token过期或无效
- `403 Forbidden`: 权限不足
- `404 Not Found`: API路径错误
- `500 Internal Server Error`: 后端错误

### 3. 样式问题

#### 检查Tailwind CSS:
```bash
# 检查Tailwind配置
cat frontend/tailwind.config.js

# 检查CSS文件
cat frontend/src/index.css | head -20

# 查看编译后的样式
# 浏览器 → F12 → Elements → 选择元素 → 查看Styles面板
```

#### 常见问题:
- **样式不生效**: 检查类名是否正确，Tailwind是否编译
- **自定义颜色不显示**: 检查`tailwind.config.js`中的颜色定义
- **响应式不工作**: 检查断点配置和类名前缀（sm:, md:, lg:）

### 4. 状态管理问题

#### 检查Context状态:
```javascript
// 在浏览器Console中检查
// 1. 检查AuthContext
localStorage.getItem('token')
localStorage.getItem('user')

// 2. 检查TradeContext
// 打开React DevTools → Components → 找到TradeProvider → 查看state

// 3. 检查AlertContext
// React DevTools → AlertProvider → 查看alerts数组
```

---

## 📊 实时日志监控

### 终端监控脚本

创建监控脚本 `monitor_frontend.sh`:
```bash
#!/bin/bash
echo "🔍 前端调试监控面板"
echo "===================="
echo ""
echo "📝 实时日志 (Ctrl+C 退出)"
echo "---"
tail -f frontend_dev.log | grep --color=always -E "error|warning|ERROR|WARNING|✓|✗" | while read line; do
    if [[ $line == *"error"* ]] || [[ $line == *"ERROR"* ]]; then
        echo -e "\033[31m$line\033[0m"  # 红色显示错误
    elif [[ $line == *"warning"* ]] || [[ $line == *"WARNING"* ]]; then
        echo -e "\033[33m$line\033[0m"  # 黄色显示警告
    elif [[ $line == *"✓"* ]]; then
        echo -e "\033[32m$line\033[0m"  # 绿色显示成功
    else
        echo "$line"
    fi
done
```

### 使用方式:
```bash
chmod +x monitor_frontend.sh
./monitor_frontend.sh
```

---

## 🌐 浏览器调试技巧

### 1. 断点调试

#### 在代码中添加断点:
```typescript
// 方式1: debugger语句（推荐）
const handleClick = () => {
  debugger; // 浏览器会在这里暂停
  console.log('点击事件');
};

// 方式2: console.log（快速调试）
console.log('🔍 调试信息:', { data, state, props });

// 方式3: console.table（表格显示）
console.table(trades); // 以表格形式显示数组
```

### 2. 网络请求调试

#### 拦截和修改请求:
```javascript
// 在Console中重写fetch
const originalFetch = window.fetch;
window.fetch = function(...args) {
  console.log('🌐 Fetch请求:', args);
  return originalFetch.apply(this, args)
    .then(response => {
      console.log('✅ Fetch响应:', response);
      return response;
    })
    .catch(error => {
      console.error('❌ Fetch错误:', error);
      throw error;
    });
};
```

### 3. 状态快照

#### 保存当前状态用于调试:
```javascript
// 在Console中执行
const debugState = {
  token: localStorage.getItem('token'),
  user: localStorage.getItem('user'),
  timestamp: new Date().toISOString()
};
console.log('📸 当前状态快照:', debugState);
// 复制到剪贴板
copy(JSON.stringify(debugState, null, 2));
```

---

## ⚡ 性能分析

### 1. React性能分析

#### 使用React DevTools Profiler:
```
1. 安装React DevTools扩展
2. 打开Profiler标签
3. 点击"Record"开始录制
4. 执行操作（点击、输入等）
5. 点击"Stop"停止录制
6. 查看性能报告:
   - 组件渲染时间
   - 渲染次数
   - 哪些组件最慢
```

### 2. 网络性能

#### Chrome Performance面板:
```
1. 打开Performance标签
2. 点击录制按钮
3. 执行操作
4. 停止录制
5. 查看:
   - 页面加载时间
   - JavaScript执行时间
   - 网络请求时间线
   - 内存使用情况
```

### 3. 内存泄漏检测

#### 检查内存使用:
```javascript
// 在Console中执行
console.log('💾 内存使用:', performance.memory);

// 强制垃圾回收（Chrome DevTools）
// Performance → Memory → 勾选"Heap snapshots"
```

---

## 🎯 调试检查清单

### 启动前检查:
- [ ] 前端依赖已安装 (`npm install`)
- [ ] 后端服务已启动 (`http://localhost:3000`)
- [ ] 端口5173未被占用
- [ ] 浏览器控制台无错误

### 运行时检查:
- [ ] 页面正常加载
- [ ] API请求成功（Network面板）
- [ ] 状态管理正常（React DevTools）
- [ ] 样式正确显示
- [ ] 交互功能正常

### 问题排查顺序:
1. ✅ 查看浏览器Console错误
2. ✅ 查看Network请求状态
3. ✅ 查看终端日志 (`tail -f frontend_dev.log`)
4. ✅ 检查React组件状态（React DevTools）
5. ✅ 检查后端日志

---

## 📱 移动端调试

### Chrome移动设备模拟:
```
1. 打开Chrome DevTools
2. 点击设备工具栏图标（或 Cmd+Shift+M）
3. 选择设备型号
4. 调整屏幕尺寸
5. 测试响应式布局
```

### 真机调试:
```
1. 确保手机和电脑在同一WiFi
2. 启动开发服务器: npm run dev -- --host
3. 在手机浏览器访问: http://<电脑IP>:5173
```

---

## 🔗 相关资源

- **Vite文档**: https://vitejs.dev/guide/
- **React文档**: https://react.dev/
- **Tailwind CSS**: https://tailwindcss.com/docs
- **Chrome DevTools**: https://developer.chrome.com/docs/devtools/

---

## 💡 调试技巧总结

1. **使用console.log分组**:
   ```javascript
   console.group('用户操作');
   console.log('步骤1:', data1);
   console.log('步骤2:', data2);
   console.groupEnd();
   ```

2. **使用console.time测量性能**:
   ```javascript
   console.time('API请求');
   await fetch('/api/trades');
   console.timeEnd('API请求'); // 显示耗时
   ```

3. **使用条件断点**:
   ```
   在Sources面板设置断点时，右键选择"Add conditional breakpoint"
   输入条件，例如: trade.id === 123
   ```

4. **保存调试会话**:
   ```
   在Console中输入的所有命令都会被保存
   使用 ↑↓ 键浏览历史命令
   ```

---

**🎉 祝调试顺利！如有问题，请查看日志文件或浏览器控制台。**
