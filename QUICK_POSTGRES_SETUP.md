# 快速PostgreSQL设置指南（5分钟完成）

## 🚀 快速开始

### 步骤1：创建Supabase项目（2分钟）

1. 访问 https://supabase.com/
2. 点击 "Start your project" → 使用GitHub登录
3. 点击 "New Project"
4. 填写：
   - **Name**: trade-view
   - **Database Password**: 设置一个强密码（**请保存！**）
   - **Region**: Southeast Asia (Singapore)
5. 点击 "Create new project"
6. 等待2-3分钟

### 步骤2：获取连接字符串（1分钟）

1. 项目创建完成后，点击左侧 **Settings** → **Database**
2. 找到 **Connection string** → 选择 **URI**
3. 复制连接字符串，格式：
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.xxxxx.supabase.co:5432/postgres
   ```
4. **替换密码**：将 `[YOUR-PASSWORD]` 替换为你设置的密码

### 步骤3：更新部署配置（1分钟）

编辑 `deploy-config.json`，添加 `DATABASE_URL`：

```json
{
  "repo_url": "https://github.com/apple-taste/trade-view",
  "service_name": "trade-view",
  "branch": "main",
  "port": 8000,
  "env_vars": {
    "NODE_ENV": "production",
    "LOG_LEVEL": "info",
    "JWT_SECRET": "your_jwt_secret_here",
    "DATABASE_URL": "postgresql://postgres:你的密码@db.xxxxx.supabase.co:5432/postgres"
  }
}
```

### 步骤4：重新部署（1分钟）

运行部署命令（代码已准备好，只需添加DATABASE_URL）：

```bash
cd /Users/ierx/cursor_workspace/trade-view
TOKEN="your_deploy_token_here"
curl -X POST "https://space.ai-builders.com/backend/v1/deployments" \
  -H "Accept: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @deploy-config.json
```

## ✅ 完成！

部署完成后：
1. ✅ 数据将永久保存
2. ✅ 重新部署不会丢失数据
3. ✅ 可以正常登录之前注册的账号

## 🔍 验证

部署后检查日志：
- ✅ 应该看到：`📦 [数据库] 使用PostgreSQL数据库`
- ❌ 不应该看到：SQLite相关日志

## 📝 示例连接字符串

```
postgresql://postgres:MySecurePassword123@db.abcdefghijklmnop.supabase.co:5432/postgres
```

**注意**：
- 替换 `MySecurePassword123` 为你的实际密码
- 替换 `abcdefghijklmnop` 为你的Supabase项目ID

## 🆘 需要帮助？

查看详细指南：`SUPABASE_SETUP.md`
