# AI 深度分析配置指南

## 概述

当前系统**已经集成**了 AI Builder Space 的 **GPT-5** 模型用于交易分析！

点击 "🤖 获取AI深度分析" 按钮时，系统会：
1. 收集所有交易历史数据
2. 调用 GPT-5 API 进行深度分析
3. 返回专业的交易分析和资金管理建议

---

## 当前状态检查

### ✅ 已实现的功能

1. **AI 分析器** (`backend/app/services/ai_analyzer.py`)
   - ✅ 使用 GPT-5 模型
   - ✅ 专业的A股交易分析
   - ✅ 科学的资金管理建议
   - ✅ 止损止盈分析
   - ✅ 入场价格分析
   - ✅ 盈亏比分析

2. **API 端点** (`backend/app/routers/analysis.py`)
   - ✅ `/api/analysis` 端点
   - ✅ 集成 ai_analyzer
   - ✅ 详细的日志输出

3. **前端按钮** (Dashboard)
   - ✅ "🤖 获取AI深度分析" 按钮
   - ✅ 调用后端 API

---

## 为什么没有看到 GPT-5 调用？

### 原因：缺少 `AI_BUILDER_TOKEN` 环境变量

代码逻辑：
```python
def __init__(self):
    # 从环境变量获取token
    self.api_key = os.getenv("AI_BUILDER_TOKEN", "")
    
async def analyze_trades_with_ai(self, trades_data, capital_history):
    if not self.api_key:
        logger.warning("AI_BUILDER_TOKEN未设置，使用基础分析")
        return self._basic_analysis(trades_data)
    
    # 如果有 token，则调用 GPT-5
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        # 调用 https://space.ai-builders.com/backend/v1/chat/completions
```

**如果没有设置 `AI_BUILDER_TOKEN`，系统会退回到基础分析模式。**

---

## 配置步骤

### 1. AI Builder Token 说明

系统使用 AI Builder Space 作为 ChatGPT-5 API 的中转站。
Token 格式: `sk_xxxxxxxx_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

### 2. 创建 `.env` 文件

在 `backend/` 目录下创建 `.env` 文件：

```bash
cd /Users/ierx/cursor_workspace/trade-view/backend
cp env.template .env
```

### 3. 配置 Token

编辑 `.env` 文件，添加您的 AI_BUILDER_TOKEN：

```env
# AI Builder Space Token - ChatGPT-5 API
AI_BUILDER_TOKEN=sk_cb7877e7_e4382f5e748e92cdd707b6f937e8cc8a5c2a

# 邮箱服务配置（如果需要）
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_FROM_EMAIL=your_email@gmail.com
```

### 4. 重启后端服务

```bash
# 停止当前运行的后端
# Ctrl+C

# 重新启动
cd /Users/ierx/cursor_workspace/trade-view/backend
python3 main.py
```

---

## 验证 AI 功能

### 1. 检查启动日志

重启后端后，应该看到：

```bash
✅ AI Builder Token已加载
```

### 2. 点击 "🤖 获取AI深度分析"

查看后端日志，应该看到：

```bash
🤖 [AI分析] 用户 xxx 请求AI分析，调用gpt-5...
📊 [AI分析] 传入数据：X条交易记录，X条资金曲线数据
🌐 [AI Builder] 正在调用 GPT-5 API...
✅ [AI分析] AI分析完成
```

### 3. 查看分析结果

如果成功调用 GPT-5，您会看到：
- 详细的止损价格分析（200字+）
- 详细的止盈价格分析（200字+）
- 详细的入场价格分析（200字+）
- 详细的盈亏比分析（200字+）
- 详细的资金管理建议（300字+）
- 关键洞察和具体建议

---

## 当前状态（无 Token 时）

### 基础分析模式

如果没有设置 `AI_BUILDER_TOKEN`，系统会使用基础分析：

**特点：**
- ✅ 仍然可以工作
- ✅ 计算基础统计数据
- ⚠️ 分析内容较简短
- ⚠️ 缺少深度洞察

**日志输出：**
```bash
⚠️ AI_BUILDER_TOKEN未设置，使用基础分析
```

---

## GPT-5 API 详细信息

### API 端点
```
POST https://space.ai-builders.com/backend/v1/chat/completions
```

### 请求头
```json
{
  "Authorization": "Bearer YOUR_TOKEN",
  "Content-Type": "application/json"
}
```

### 请求体
```json
{
  "model": "gpt-5",
  "messages": [
    {
      "role": "system",
      "content": "你是一位专业的A股交易分析师..."
    },
    {
      "role": "user",
      "content": "分析提示..."
    }
  ],
  "temperature": 1.0,
  "max_completion_tokens": 3000
}
```

### GPT-5 特殊要求
- ✅ `temperature` 必须为 `1.0`
- ✅ 使用 `max_completion_tokens`（不是 `max_tokens`）
- ✅ 支持最多 3000 tokens 的响应

---

## 故障排查

### 问题：看不到 GPT-5 调用日志

**检查清单：**
1. ✅ 检查是否创建了 `.env` 文件
2. ✅ 检查 `AI_BUILDER_TOKEN` 是否正确
3. ✅ 检查是否重启了后端服务
4. ✅ 查看日志是否有 "AI_BUILDER_TOKEN未设置" 警告

### 问题：API 调用失败

**可能原因：**
1. Token 已过期或无效
2. 网络连接问题
3. API 服务暂时不可用

**查看详细错误：**
```bash
tail -f /Users/ierx/cursor_workspace/trade-view/backend/backend.log
```

---

## 代码位置

### AI 分析器
```
backend/app/services/ai_analyzer.py
- 第11行：AIAnalyzer 类
- 第15行：读取 AI_BUILDER_TOKEN
- 第19行：analyze_trades_with_ai 方法
- 第52行：调用 GPT-5 API
```

### API 路由
```
backend/app/routers/analysis.py
- 第11行：导入 ai_analyzer
- 第244行：调用 AI 分析
```

### 前端调用
```
frontend/src/components/panels/AnalysisPanel.tsx
- 获取AI深度分析按钮
```

---

## 总结

✅ **已实现**：GPT-5 集成代码已完成
⚠️ **需要配置**：添加 `AI_BUILDER_TOKEN` 到 `.env` 文件
🔄 **需要重启**：修改 `.env` 后重启后端

配置完成后，您的 "🤖 获取AI深度分析" 功能将使用 GPT-5 提供专业的交易分析！🚀
