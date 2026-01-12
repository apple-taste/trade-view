# 闹铃系统设置指南

## 🎵 功能概述

Trade View 提供了完整的价格闹铃系统，包括：

1. **JOJO风格铃声** - 浏览器内播放自定义音频
2. **铃声开关** - 一键开启/关闭声音提醒
3. **音量控制** - 调节铃声音量（0-100%）
4. **邮件通知** - 通过邮件接收价格提醒
5. **自动监控** - 后台自动检测止损/止盈条件

---

## 🎼 1. 添加JOJO风格铃声

### 步骤1：准备音频文件

1. 找一个JOJO风格的音频文件（推荐格式：MP3）
   - 推荐：「Stand Proud」或「Giorno's Theme」的片段
   - 时长：3-5秒最佳
   - 大小：建议 < 1MB

2. 将音频文件命名为 `jojo-alert.mp3`

3. 放置到项目路径：
   ```
   trade-view/frontend/public/jojo-alert.mp3
   ```

### 步骤2：测试铃声

1. 重启前端服务：
   ```bash
   cd frontend
   npm run dev
   ```

2. 打开浏览器，价格提醒触发时会自动播放铃声

3. 点击铃声开关按钮测试：
   - 🔊 图标：铃声已开启
   - 🔇 图标：铃声已关闭

---

## 📧 2. 配置邮件提醒

### Gmail 配置（推荐）

1. **创建应用专用密码**
   - 访问：https://myaccount.google.com/apppasswords
   - 选择应用："邮件"
   - 选择设备："其他（自定义名称）" → 输入 "Trade View"
   - 点击"生成"，复制16位密码

2. **配置环境变量**
   ```bash
   cd backend
   cp .env.example .env
   ```
   
   编辑 `.env` 文件：
   ```bash
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your-email@gmail.com
   SMTP_PASSWORD=生成的16位密码
   SENDER_EMAIL=your-email@gmail.com
   SENDER_NAME=Trade View 价格提醒
   ```

3. **重启后端服务**
   ```bash
   python3 main.py
   ```

### QQ邮箱配置

1. **获取授权码**
   - 登录 QQ邮箱：https://mail.qq.com
   - 进入"设置" → "账户"
   - 找到"POP3/IMAP/SMTP服务"
   - 开启"IMAP/SMTP服务"
   - 点击"生成授权码"，保存授权码

2. **配置环境变量**
   ```bash
   SMTP_SERVER=smtp.qq.com
   SMTP_PORT=587
   SMTP_USERNAME=your-qq@qq.com
   SMTP_PASSWORD=获取的授权码
   SENDER_EMAIL=your-qq@qq.com
   ```

### 163邮箱配置

```bash
SMTP_SERVER=smtp.163.com
SMTP_PORT=587
SMTP_USERNAME=your-email@163.com
SMTP_PASSWORD=获取的授权码
```

---

## ⚙️ 3. 使用闹铃功能

### 前端操作

1. **开启铃声**
   - 在闹铃提醒面板（黄色边框）右上角
   - 点击🔊图标开启/关闭铃声
   - 点击百分比数字调整音量滑块

2. **开启邮件提醒**
   - 在用户面板（User Panel）
   - 找到"📧 邮箱闹铃提醒"开关
   - 切换开关即可启用/禁用邮件通知

3. **设置止损/止盈闹铃**
   - 在"开仓记录"中添加持仓时
   - 勾选"止损价格闹铃"或"止盈价格闹铃"
   - 设置对应的价格阈值

### 闹铃触发条件

- **止损闹铃**：当前价格 ≤ 止损价格
- **止盈闹铃**：当前价格 ≥ 止盈价格

### 闹铃通知方式

| 通知方式 | 触发条件 | 说明 |
|---------|---------|------|
| 浏览器铃声 | 价格触及 + 铃声开启 | 即时播放JOJO音效 |
| 浏览器通知 | 价格触及 | 系统桌面通知 |
| 邮件通知 | 价格触及 + 邮箱提醒开启 | 发送HTML格式邮件 |

---

## 🔧 4. 高级设置

### 调整监控频率

编辑 `backend/app/services/alert_monitor.py`：

```python
class AlertMonitor:
    def __init__(self):
        self.check_interval = 10  # 修改此值（单位：秒）
```

### 调整价格更新频率

编辑 `backend/app/services/price_monitor.py`：

```python
class PriceMonitor:
    def __init__(self):
        self.update_interval = 5  # 修改此值（单位：秒）
```

### 自定义邮件模板

编辑 `backend/app/services/email_service.py` 中的 `html_body` 部分。

---

## 🐛 故障排查

### 铃声不播放

1. **检查音频文件**
   ```bash
   ls -lh frontend/public/jojo-alert.mp3
   ```

2. **浏览器自动播放限制**
   - Chrome/Edge：首次访问需要用户交互后才能播放音频
   - 解决：点击页面任意位置后，铃声即可正常工作

3. **检查铃声开关状态**
   - 确保🔊图标显示（而非🔇）

### 邮件不发送

1. **检查环境变量**
   ```bash
   cd backend
   cat .env | grep SMTP
   ```

2. **检查邮箱提醒开关**
   - 用户面板中的"📧 邮箱闹铃提醒"必须开启

3. **查看后端日志**
   ```bash
   # 日志中会显示邮件发送状态
   ✅ 邮件发送成功: user@example.com - 600000 stop_loss
   ❌ 邮件发送失败: user@example.com - 600000 - error message
   ```

4. **测试SMTP连接**
   ```python
   python3 -c "
   from app.services.email_service import default_email_service
   print('SMTP已配置:', default_email_service.is_configured())
   "
   ```

---

## 📝 注意事项

1. **隐私安全**
   - 不要将 `.env` 文件提交到Git
   - 使用应用专用密码，不要使用真实邮箱密码

2. **频率限制**
   - 相同股票的相同闹铃类型，10秒内只触发一次（防止频繁通知）
   - Gmail有发送频率限制（约500封/天）

3. **取消闹铃**
   - 平仓后，该持仓的闹铃会自动清除
   - 关闭闹铃开关（复选框取消勾选）

4. **邮件模板**
   - 邮件采用JOJO风格的HTML模板
   - 包含股票代码、当前价格、目标价格等信息

---

## 🎨 邮件预览

邮件采用JOJO Land风格设计：

- 金色边框（#FFD700）
- 深蓝背景（#0f3460）
- 渐变色卡片阴影
- 大号emoji表情
- 响应式布局

---

## 💡 推荐配置

```bash
# .env 文件示例（Gmail）
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx
SENDER_EMAIL=your-email@gmail.com
SENDER_NAME=Trade View 闹铃机器人
```

**完成配置后，重启后端服务即可生效！** 🎉
