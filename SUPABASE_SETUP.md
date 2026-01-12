# Supabase PostgreSQL 设置指南

## 为什么使用Supabase？

- ✅ **免费**：500MB数据库 + 2GB带宽/月
- ✅ **简单**：5分钟完成设置
- ✅ **可靠**：基于PostgreSQL，数据永久保存
- ✅ **自动备份**：每日自动备份
- ✅ **无需维护**：完全托管服务

## 设置步骤

### 1. 创建Supabase账号

1. 访问 https://supabase.com/
2. 点击 "Start your project"
3. 使用GitHub账号登录（推荐）或邮箱注册

### 2. 创建新项目

1. 点击 "New Project"
2. 填写项目信息：
   - **Name**: trade-view（或你喜欢的名字）
   - **Database Password**: 设置一个强密码（**重要！请保存**）
   - **Region**: 选择离你最近的区域（推荐：Southeast Asia (Singapore)）
3. 点击 "Create new project"
4. 等待2-3分钟让项目创建完成

### 3. 获取数据库连接字符串

1. 在项目页面，点击左侧菜单的 **Settings**（设置）
2. 点击 **Database**
3. 找到 **Connection string** 部分
4. 选择 **URI** 标签
5. 复制连接字符串，格式类似：
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.xxxxx.supabase.co:5432/postgres
   ```
6. **重要**：将 `[YOUR-PASSWORD]` 替换为你创建项目时设置的密码

### 4. 配置环境变量

将连接字符串添加到 `deploy-config.json`：

```json
{
  "env_vars": {
    "DATABASE_URL": "postgresql://postgres:你的密码@db.xxxxx.supabase.co:5432/postgres"
  }
}
```

### 5. 测试连接

部署后，检查日志确认数据库连接成功：
- 应该看到：`📦 [数据库] 使用PostgreSQL数据库`
- 不应该看到SQLite相关日志

## 安全提示

⚠️ **重要**：
- 不要在代码中硬编码密码
- 使用环境变量存储连接字符串
- 定期更换数据库密码
- 不要将包含密码的配置文件提交到GitHub

## 免费额度

Supabase免费计划包括：
- ✅ 500MB数据库存储
- ✅ 2GB带宽/月
- ✅ 每日自动备份
- ✅ 无限API请求

对于个人项目完全够用！

## 其他PostgreSQL服务

如果不想使用Supabase，也可以使用：

1. **Railway** (https://railway.app/)
   - 免费额度：$5/月
   - 简单易用

2. **Neon** (https://neon.tech/)
   - 免费PostgreSQL
   - 按需扩展

3. **ElephantSQL** (https://www.elephantsql.com/)
   - 免费计划：20MB数据库
   - 适合小型项目

## 故障排查

### 问题：连接失败

1. 检查密码是否正确
2. 检查连接字符串格式
3. 确认项目已创建完成（等待2-3分钟）

### 问题：表不存在

1. 应用启动时会自动创建表
2. 检查日志中的数据库初始化信息
3. 如果表未创建，检查数据库连接是否成功

### 问题：数据丢失

1. Supabase会自动备份数据
2. 可以在Supabase控制台查看数据
3. 数据不会因为重新部署而丢失

## 下一步

1. ✅ 创建Supabase项目
2. ✅ 获取连接字符串
3. ✅ 更新 `deploy-config.json`
4. ✅ 重新部署应用
5. ✅ 验证数据持久化

完成以上步骤后，你的数据将永久保存，不会因为重新部署而丢失！
