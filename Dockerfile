# 多阶段构建：构建前端
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# 复制前端依赖文件
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# 复制前端源代码并构建
COPY frontend/ .
RUN npm run build

# 生产阶段：运行后端并服务前端
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制后端依赖文件
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY backend/ .

# 从前端构建阶段复制构建产物
COPY --from=frontend-builder /app/frontend/dist ./static

# 创建静态文件目录（如果不存在）
RUN mkdir -p ./static

# 暴露端口（PORT将在运行时由Koyeb设置）
EXPOSE 8000

# 启动应用，使用PORT环境变量
# 使用shell形式确保环境变量正确扩展
CMD sh -c "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"
