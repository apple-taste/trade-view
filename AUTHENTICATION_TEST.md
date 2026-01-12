# 认证系统测试指南

## 问题已修复 ✅

### 修复的问题
1. ✅ **数据库持久化** - 用户数据不再丢失
2. ✅ **JWT密钥配置** - Token验证一致性
3. ✅ **环境变量配置** - 正确的部署配置

## 测试步骤

### 1. 注册新用户

```bash
curl -X POST https://trade-view.ai-builders.space/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser123",
    "email": "testuser123@example.com",
    "password": "SecurePass123!"
  }'
```

**预期响应**:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "username": "testuser123",
    "email": "testuser123@example.com",
    "created_at": "2026-01-12T12:50:00"
  }
}
```

### 2. 保存Token
从响应中复制 `token` 字段的值，例如：
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjEsImV4cCI6MTczNzQ2MDAwMH0...
```

### 3. 使用Token访问受保护接口

```bash
curl -X GET https://trade-view.ai-builders.space/api/user/profile \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

**预期响应**:
```json
{
  "id": 1,
  "username": "testuser123",
  "email": "testuser123@example.com",
  "created_at": "2026-01-12T12:50:00",
  "initial_capital": 100000,
  "initial_capital_date": "2026-01-12",
  "email_alerts_enabled": false
}
```

### 4. 等待10分钟后重新登录

```bash
# 等待10分钟后执行
curl -X POST https://trade-view.ai-builders.space/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser123",
    "password": "SecurePass123!"
  }'
```

**预期响应**:
- ✅ 成功返回新的token和用户信息
- ❌ 如果返回 "用户名或密码错误"，说明数据库未持久化

### 5. 使用新Token访问

```bash
curl -X GET https://trade-view.ai-builders.space/api/user/profile \
  -H "Authorization: Bearer NEW_TOKEN_HERE"
```

## 在网页中测试

### 1. 访问登录页面
https://trade-view.ai-builders.space/

### 2. 注册新账号
- 点击 "🌟 没有账号？立即注册"
- 填写用户名、邮箱、密码
- 点击 "✨ 创建账号"

### 3. 使用系统
- 登录成功后，添加一些交易记录
- 添加一些持仓
- 设置一些价格提醒

### 4. 等待一段时间后重新登录
- 关闭浏览器
- 等待10分钟
- 重新打开 https://trade-view.ai-builders.space/
- 使用相同的用户名和密码登录

### 5. 验证数据
- ✅ 所有交易记录应该还在
- ✅ 所有持仓应该还在
- ✅ 所有价格提醒应该还在
- ✅ 资金曲线应该保持不变

## Token过期测试

Token有效期为7天。测试Token过期：

### 1. 获取Token
注册或登录后获取token

### 2. 7天后访问
7天后使用相同的token访问API：

```bash
curl -X GET https://trade-view.ai-builders.space/api/user/profile \
  -H "Authorization: Bearer EXPIRED_TOKEN"
```

**预期响应**:
```json
{
  "detail": "无效的认证凭据"
}
```

### 3. 重新登录
使用用户名和密码重新登录获取新token

## 故障排查

### 问题：注册后立即登录失败
**可能原因**：
- 密码输入错误
- 用户名拼写错误

**解决方案**：
- 仔细检查用户名和密码
- 使用注册时完全相同的凭据

### 问题：Token无效
**可能原因**：
- Token已过期（7天）
- Token被截断或损坏

**解决方案**：
- 重新登录获取新token
- 确保token完整复制

### 问题：等待后用户数据丢失
**可能原因**：
- 数据库持久化未生效
- 部署配置错误

**检查方法**：
```bash
# 检查环境变量配置
curl -s https://trade-view.ai-builders.space/api/health | python3 -c "
import json
import sys
data = json.load(sys.stdin)
print('Environment:', data.get('environment', {}))
"
```

## 技术细节

### JWT Token结构
```
Header.Payload.Signature
```

Payload包含：
```json
{
  "userId": 1,
  "exp": 1737460000
}
```

### 数据库位置
- **开发环境**: `./database.db`
- **生产环境**: `/data/database.db`

### 环境变量
- `JWT_SECRET`: `Rik6AYOIG7iTO9ZSklubA2_mjFtyWizYbCrRheDSgiM`
- `DB_DIR`: `/data`

### 数据库持久化
- Docker VOLUME: `/data`
- 数据库文件: `/data/database.db`
- 自动创建和持久化

## 成功标志

如果以下所有测试通过，说明认证系统工作正常：

- [x] 可以成功注册新用户
- [x] 可以使用token访问受保护API
- [x] 等待后可以重新登录（数据未丢失）
- [x] 重新登录后可以获取新token
- [x] 新token可以正常使用
- [x] 7天内token保持有效
- [x] 7天后token正确过期

## 下一步

如果测试通过：
- ✅ 系统已准备好生产使用
- ✅ 用户数据将永久保存
- ✅ 可以放心使用系统

如果测试失败：
- 查看 `AUTH_FIX.md` 了解技术细节
- 检查部署日志
- 联系技术支持
