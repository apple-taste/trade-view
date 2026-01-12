# Koyeb 持久化存储配置

## 问题
Koyeb可能不支持Dockerfile中的VOLUME声明，导致数据库在重新部署时丢失。

## 解决方案
Koyeb使用自己的持久化存储机制。我们需要：
1. 使用Koyeb的环境变量配置持久化路径
2. 或者使用Koyeb的持久化卷功能（如果支持）

## 当前配置
- DB_DIR=/data
- 数据库路径: /data/database.db

## 备选方案
如果Koyeb不支持持久化卷，我们需要：
1. 使用外部数据库（PostgreSQL）
2. 或者每次部署时重新注册用户
