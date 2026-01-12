# 迁移到PostgreSQL数据库指南

## 为什么需要迁移？

Koyeb不支持Dockerfile中的VOLUME声明，每次重新部署都会丢失SQLite数据库数据。

## 解决方案：使用PostgreSQL

### 选项1：使用Koyeb的PostgreSQL插件（如果可用）

### 选项2：使用外部PostgreSQL服务

推荐服务：
- **Supabase**（免费额度充足）
- **Railway**（免费额度）
- **Neon**（免费PostgreSQL）
- **ElephantSQL**（免费计划）

### 选项3：使用SQLite + 定期备份（临时方案）

如果不想迁移到PostgreSQL，可以：
1. 定期备份数据库文件
2. 部署时恢复备份
3. 但这需要手动操作，不够自动化

## 快速修复（临时方案）

如果暂时无法迁移到PostgreSQL，可以：

1. **每次部署后重新注册账号**
2. **或者使用环境变量保存数据库到Koyeb的持久化存储**（如果Koyeb支持）

## 当前状态

- ✅ 已添加详细的数据库日志
- ✅ 已配置`DB_DIR`环境变量
- ⚠️  Koyeb不支持VOLUME挂载
- ⚠️  每次重新部署数据会丢失

## 建议

**短期**：每次部署后重新注册账号
**长期**：迁移到PostgreSQL数据库
