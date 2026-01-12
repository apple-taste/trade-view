# 🚀 部署指南

## 📋 前置步骤

### 1. 创建GitHub仓库

由于GitHub不再支持密码认证，请按以下步骤操作：

**方法1：使用GitHub网页（推荐）**
1. 访问：https://github.com/new
2. Owner: `apple-taste`
3. Repository name: `trade-view`
4. Description: `A股交易管理系统 - A股个人交易管理应用`
5. 选择：**Public**
6. **不要**勾选"Initialize this repository with:"
7. 点击"Create repository"

**方法2：使用GitHub CLI**
```bash
gh repo create apple-taste/trade-view --public --description "A股交易管理系统"
```

### 2. 推送代码到GitHub

创建仓库后，推送代码：

```bash
cd /Users/ierx/cursor_workspace/trade-view
git push -u origin main
```

**如果提示认证：**
- GitHub不再支持密码认证
- 需要使用Personal Access Token (PAT)
- 创建PAT：https://github.com/settings/tokens
- 选择权限：`repo`（全部权限）
- 推送时使用PAT作为密码

### 3. 验证仓库已创建

访问：https://github.com/apple-taste/trade-view

确认代码已成功推送。

## 🚀 部署到AI Builder Space

部署配置已准备好：
- **仓库URL**: `https://github.com/apple-taste/trade-view`
- **服务名称**: `trade-view`
- **分支**: `main`
- **端口**: `8000`

部署后，您的应用将在以下地址可用：
**https://trade-view.ai-builders.space**

## 📝 部署配置

配置文件：`deploy-config.json`

```json
{
  "repo_url": "https://github.com/apple-taste/trade-view",
  "service_name": "trade-view",
  "branch": "main",
  "port": 8000,
  "env_vars": {
    "NODE_ENV": "production",
    "LOG_LEVEL": "info"
  }
}
```

## ✅ 部署检查清单

- [x] Dockerfile已创建
- [x] main.py已支持PORT环境变量
- [x] 静态文件服务已配置
- [x] Git仓库已初始化
- [x] 代码已提交
- [ ] GitHub仓库已创建（需要您手动完成）
- [ ] 代码已推送到GitHub（需要您手动完成）
- [ ] 使用MCP部署API进行部署

## 🔧 部署后检查

部署完成后，检查以下内容：

1. **健康检查**: https://trade-view.ai-builders.space/api/health
2. **API文档**: https://trade-view.ai-builders.space/docs
3. **前端应用**: https://trade-view.ai-builders.space

## 📞 需要帮助？

如果部署遇到问题：
1. 检查部署日志
2. 查看Koyeb状态
3. 联系instructor获取支持
