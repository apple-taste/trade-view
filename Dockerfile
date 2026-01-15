# 多阶段构建：构建前端
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# 复制前端依赖文件
COPY frontend/package.json ./
# 如果package-lock.json存在则复制，否则使用npm install
COPY frontend/package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

# 复制前端源代码并构建
COPY frontend/ .
# 强制刷新缓存: v1.1.3-fix
ENV FORCE_REBUILD=20260115-1500
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

# 创建数据目录用于数据库持久化
RUN mkdir -p /data

# 设置数据目录环境变量
ENV DB_DIR=/data

# 暴露端口（PORT将在运行时由Koyeb设置）
EXPOSE 8000
VOLUME ["/data"]

# 启动应用，使用PORT环境变量
# 使用shell形式确保环境变量正确扩展
# 注意：main.py在/app目录下，所以直接使用main:app
# 添加--timeout-keep-alive以确保连接保持
# 使用--workers 1确保单进程（符合部署要求）
CMD sh -c "cd /app && python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --log-level info --timeout-keep-alive 30 --workers 1"
