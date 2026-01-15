# 部署使用说明（DEPLOY_USAGE）

本文档说明本项目的两部分操作：
- 如何把本地代码上传到 GitHub 仓库 `apple-taste/trade-view`
- 如何通过 AI Builder Space 部署到线上（`https://trade-view.ai-builders.space/`）

---

## 一、上传代码到 GitHub

### 1. 前提条件

- 已安装 Git
- 已在终端进入项目根目录：

  ```bash
  cd /Users/ierx/cursor_workspace/trade-view
  ```

### 2. 准备 GitHub Personal Access Token（PAT）

1. 打开：https://github.com/settings/tokens/new
2. 选择 “Generate new token (classic)”
3. 勾选权限：`repo`（全部）
4. 生成后复制这个 Token（后续会作为参数传给脚本）

### 3. 首次初始化并推送：`setup_github.sh`

首次使用时，推荐用仓库自带的脚本完成初始化和首推：

```bash
cd /Users/ierx/cursor_workspace/trade-view
chmod +x setup_github.sh
./setup_github.sh YOUR_GITHUB_PAT
```

> 将 `YOUR_GITHUB_PAT` 替换为你刚刚生成的 GitHub Token。

脚本会完成：
- 检查/创建 GitHub 仓库 `apple-taste/trade-view`
- 本地执行 `git init`、`git add .`、`git commit`、`git branch -M main`
- 配置远程 origin，并推送到 `main` 分支

之后你就可以用普通的 Git 命令继续开发和推送。

### 4. 日常提交与推送（手动方式）

如果不使用后面的一键脚本，可以直接按 Git 标准流程：

```bash
cd /Users/ierx/cursor_workspace/trade-view

git status
git add .
git commit -m "本次修改说明"
git push origin main
```

推送完成后，GitHub 仓库 `https://github.com/apple-taste/trade-view` 的 `main` 分支会同步最新代码。

---

## 二、部署到 AI Builder Space

当前部署由三个脚本配合完成：
- `deploy.sh`：触发部署
- `check-deployment.sh`：查看部署状态和日志
- `push_and_deploy.sh`（你即将使用的一键脚本）：提交 + 推送 + 部署

### 1. 配置 `.env`

项目根目录应存在 `.env` 文件，其中至少需要：

- `DEPLOY_TOKEN`：AI Builder Space 提供的部署 Token（必需）
- `GITHUB_REPO_NAME`（可选，默认 `trade-view`）
- `GITHUB_REPO_OWNER`（可选，默认 `apple-taste`）
- `GITHUB_BRANCH`（可选，默认 `main`）

`.env` 中包含敏感信息，不建议推送到公开仓库。

### 2. 检查 `deploy-config.json`

根目录有 `deploy-config.json`，主要字段：

- `repo_url`：GitHub 仓库地址，例如 `https://github.com/apple-taste/trade-view`
- `service_name`：服务名称，例如 `trade-view`
- `branch`：部署分支，例如 `main`
- `port`：容器内后端监听端口，例如 `8000`
- `env_vars`：线上环境变量（数据库、密钥等）

如需更换数据库、密钥等，请在此文件里调整对应值。

### 3. 触发部署：`deploy.sh`

```bash
cd /Users/ierx/cursor_workspace/trade-view
chmod +x deploy.sh
./deploy.sh
```

脚本会：
- 从 `.env` 加载配置
- 调用 AI Builder Space 的 `/deployments` 接口提交部署请求
- 输出服务名、状态、提示信息

部署请求提交后，通常需要等待 5–10 分钟构建并启动服务。

### 4. 查看部署状态和日志：`check-deployment.sh`

```bash
cd /Users/ierx/cursor_workspace/trade-view
chmod +x check-deployment.sh
./check-deployment.sh
```

脚本会显示：
- 服务当前状态（`status` / `koyeb_status`）
- 使用的仓库、分支、公共 URL
- 最近部署时间、消息
- 最近的构建日志和运行错误日志
- 对 `https://trade-view.ai-builders.space/api/health` 的健康检查结果

### 5. 访问线上服务

- Web 入口：`https://trade-view.ai-builders.space/`
- 健康检查：`https://trade-view.ai-builders.space/api/health`

如果前端有更新但浏览器看不到新界面，建议：
- 使用强制刷新（如 `Cmd + Shift + R`）
- 或使用浏览器隐身/无痕模式重新打开

---

## 三、一键提交 + 推送 + 部署：`push_and_deploy.sh`

仓库根目录会提供一个一键脚本 `push_and_deploy.sh`，用于把常用流程串起来：

1. `git add .`
2. `git commit -m "你的提交信息"`
3. `git push origin main`
4. `./deploy.sh`

### 1. 使用方式

先赋予执行权限（只需一次）：

```bash
cd /Users/ierx/cursor_workspace/trade-view
chmod +x push_and_deploy.sh
```

执行时传入本次提交信息，例如：

```bash
./push_and_deploy.sh "更新外汇资金曲线和部署脚本"
```

脚本行为：
- 如果工作区没有变更，跳过 commit 但仍会执行 `git push origin main` 和 `./deploy.sh`
- 如果有变更，会自动 `git add .` 并创建一次 commit

### 2. 典型工作流示例

日常开发建议流程：

```bash
cd /Users/ierx/cursor_workspace/trade-view

# 本地开发、跑前后端、本地确认没问题后

./push_and_deploy.sh "描述本次修改"

# 等待 5–10 分钟，然后
./check-deployment.sh

# 浏览器访问：
#   https://trade-view.ai-builders.space/
```

当你希望更细粒度控制（例如手动分几次 commit），也可以只用普通 `git add/commit/push`，最后单独执行：

```bash
./deploy.sh
./check-deployment.sh
```

---

如有其它部署平台或多环境需求，可以在此文档基础上继续扩展新的小节。

