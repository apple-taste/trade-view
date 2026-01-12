# 认证问题修复说明

## 问题分析

### 1. 用户数据丢失问题
**原因**: Docker容器中的SQLite数据库没有持久化
- 数据库文件位于容器内的 `/app/database.db`
- 容器重启/重新部署时，数据库文件丢失
- 导致所有用户账号消失

### 2. Token失效问题
**原因**: JWT_SECRET未正确配置
- 使用默认密钥 `"your-secret-key-change-in-production"`
- 容器重启后可能使用不同的密钥
- 导致之前签发的token无法验证

## 修复方案

### 1. 数据库持久化 ✅
修改 `backend/app/database.py`:
```python
# 数据库文件路径（确保持久化）
DB_DIR = Path(os.getenv("DB_DIR", "."))
DB_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_PATH = DB_DIR / "database.db"
DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_PATH}"
```

修改 `Dockerfile`:
```dockerfile
# 创建数据目录用于数据库持久化
RUN mkdir -p /data
ENV DB_DIR=/data
VOLUME ["/data"]
```

### 2. JWT密钥配置 ✅
更新 `backend/env.template`:
```bash
# JWT 认证密钥（重要！）
JWT_SECRET=your-secret-key-change-in-production
```

### 3. 部署环境变量配置
需要在部署时设置以下环境变量：
- `JWT_SECRET`: 强密码（建议32字符以上）
- `DB_DIR`: `/data`（数据库持久化目录）

## 生成JWT密钥

使用以下命令生成强密码：
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

示例输出：
```
Rik6AYOIG7iTO9ZSklubA2_mjFtyWizYbCrRheDSgiM
```

## 注意事项

1. **JWT_SECRET必须保持一致**
   - 部署后不要随意更改
   - 更改后所有用户需要重新登录

2. **数据库持久化**
   - Docker容器需要挂载 `/data` 目录
   - Koyeb等平台会自动处理持久化卷

3. **首次部署**
   - 如果之前有用户数据，首次使用持久化后需要重新注册
   - 这是因为之前的数据在容器中已经丢失

## 验证方法

1. **注册新用户**
   ```bash
   curl -X POST https://trade-view.ai-builders.space/api/auth/register \
     -H "Content-Type: application/json" \
     -d '{"username":"test","email":"test@example.com","password":"password123"}'
   ```

2. **等待5分钟后重新登录**
   ```bash
   curl -X POST https://trade-view.ai-builders.space/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username":"test","password":"password123"}'
   ```

3. **应该成功返回token**
   - 如果返回token，说明持久化成功
   - 如果返回"用户名或密码错误"，说明数据丢失

## 技术细节

### Token过期时间
- 设置为7天：`expire = datetime.utcnow() + timedelta(days=7)`
- Token payload: `{"userId": user_id, "exp": expire}`

### 密码加密
- 使用 `pbkdf2_sha256` 算法
- 更兼容，无bcrypt版本依赖问题

### 数据库引擎
- SQLite + aiosqlite（异步）
- 生产环境建议使用PostgreSQL
