# 邮件服务配置说明

## 📧 配置环境变量

创建 `backend/.env` 文件，添加以下配置：

```bash
# SMTP服务器配置
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SENDER_EMAIL=your-email@gmail.com
SENDER_NAME=Trade View 价格提醒
```

## 🔧 各邮箱服务商配置

### Gmail

```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=应用专用密码（16位）
```

**获取应用专用密码**：
1. 访问 https://myaccount.google.com/apppasswords
2. 选择应用："邮件"
3. 选择设备："其他" → 输入 "Trade View"
4. 复制生成的16位密码

### QQ邮箱

```bash
SMTP_SERVER=smtp.qq.com
SMTP_PORT=587
SMTP_USERNAME=your-qq@qq.com
SMTP_PASSWORD=授权码
```

**获取授权码**：
1. 登录 QQ邮箱：https://mail.qq.com
2. 设置 → 账户 → POP3/IMAP/SMTP服务
3. 开启"IMAP/SMTP服务"
4. 点击"生成授权码"

### 163邮箱

```bash
SMTP_SERVER=smtp.163.com
SMTP_PORT=587
SMTP_USERNAME=your-email@163.com
SMTP_PASSWORD=授权码
```

## ⚠️ 注意事项

1. **不要提交 .env 文件到Git**
2. **使用应用专用密码，不要使用真实邮箱密码**
3. **Gmail有发送频率限制（约500封/天）**
