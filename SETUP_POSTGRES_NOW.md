# 🚀 立即设置PostgreSQL数据库（5分钟完成）

## 步骤1：创建Supabase项目（2分钟）

1. **打开浏览器**，访问：https://supabase.com/

2. **点击右上角** "Start your project"

3. **选择登录方式**（推荐使用GitHub账号，更快速）

4. **登录后**，点击 "New Project" 按钮

5. **填写项目信息**：
   - **Name**: `trade-view`（或你喜欢的名字）
   - **Database Password**: 设置一个强密码（⚠️ **请务必保存这个密码！**）
   - **Region**: 选择 `Southeast Asia (Singapore)` 或离你最近的区域

6. **点击** "Create new project"

7. **等待2-3分钟**让项目创建完成（会显示进度条）

## 步骤2：获取数据库连接字符串（1分钟）

项目创建完成后：

1. 在Supabase项目页面，点击左侧菜单的 **Settings**（⚙️ 设置图标）

2. 点击 **Database**

3. 向下滚动找到 **Connection string** 部分

4. 点击 **URI** 标签（不是其他标签）

5. 你会看到一个连接字符串，格式类似：
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.xxxxx.supabase.co:5432/postgres
   ```

6. **复制这个连接字符串**

7. ⚠️ **重要**：将 `[YOUR-PASSWORD]` 替换为你创建项目时设置的密码

   **示例**：
   - 如果连接字符串是：`postgresql://postgres:[YOUR-PASSWORD]@db.abcdefghijklmnop.supabase.co:5432/postgres`
   - 你的密码是：`MySecurePassword123`
   - 那么最终连接字符串应该是：`postgresql://postgres:MySecurePassword123@db.abcdefghijklmnop.supabase.co:5432/postgres`

## 步骤3：更新部署配置（1分钟）

编辑 `deploy-config.json` 文件，在 `env_vars` 中添加 `DATABASE_URL`：

**当前配置**：
```json
{
  "env_vars": {
    "NODE_ENV": "production",
    "LOG_LEVEL": "info",
    "JWT_SECRET": "your_jwt_secret_here",
    "DB_DIR": "/data"
  }
}
```

**更新后**（添加 `DATABASE_URL`）：
```json
{
  "env_vars": {
    "NODE_ENV": "production",
    "LOG_LEVEL": "info",
    "JWT_SECRET": "your_jwt_secret_here",
    "DATABASE_URL": "postgresql://postgres:你的密码@db.xxxxx.supabase.co:5432/postgres"
  }
}
```

**注意**：将 `你的密码` 和 `xxxxx` 替换为你的实际值。

## 步骤4：提交并部署（1分钟）

运行以下命令：

```bash
cd /Users/ierx/cursor_workspace/trade-view

# 1. 提交配置
git add deploy-config.json
git commit -m "Add PostgreSQL DATABASE_URL for data persistence"
git push origin main

# 2. 重新部署
TOKEN="your_deploy_token_here"
curl -X POST "https://space.ai-builders.com/backend/v1/deployments" \
  -H "Accept: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @deploy-config.json
```

## ✅ 完成！

部署完成后（等待5-10分钟）：

1. ✅ 数据将永久保存
2. ✅ 重新部署不会丢失数据
3. ✅ 可以正常登录之前注册的账号

## 🔍 验证方法

部署后检查日志，应该看到：
```
📦 [数据库] 使用PostgreSQL数据库
```

**而不是**：
```
📦 [数据库] 使用SQLite数据库
```

## 🆘 需要帮助？

如果遇到问题：
1. 检查连接字符串格式是否正确
2. 确认密码已正确替换（没有 `[YOUR-PASSWORD]` 占位符）
3. 确认Supabase项目已创建完成
4. 查看部署日志确认数据库连接成功

## 📝 示例

**完整的连接字符串示例**：
```
postgresql://postgres:MySecurePassword123@db.abcdefghijklmnop.supabase.co:5432/postgres
```

**deploy-config.json 示例**：
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
    "DATABASE_URL": "postgresql://postgres:MySecurePassword123@db.abcdefghijklmnop.supabase.co:5432/postgres"
  }
}
```

---

**准备好了吗？** 按照上面的步骤操作，5分钟后你的数据就会永久保存了！🎉
