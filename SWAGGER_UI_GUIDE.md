# 📚 FastAPI Swagger UI 使用指南

## 🎯 什么是 Swagger UI？

Swagger UI 是 FastAPI 自动生成的交互式 API 文档界面，让你可以：
- 📖 查看所有API接口
- 🧪 直接在浏览器中测试API
- 📝 查看请求/响应格式
- 🔑 测试认证功能

## 🚀 访问 Swagger UI

启动后端服务后，访问：
- **Swagger UI**: http://localhost:3000/docs
- **ReDoc** (另一种文档格式): http://localhost:3000/redoc

## 📖 界面说明

### 1. 顶部信息栏
- **API标题**: A股交易管理系统 API
- **版本**: 1.0.0
- **服务器地址**: http://localhost:3000
- **Authorize按钮**: 🔑 用于设置认证Token

### 2. API分组（Tags）
API按功能模块分组：
- 🔐 **认证** - 注册、登录
- 👤 **用户** - 用户信息、资金管理
- 📝 **交易记录** - 交易记录的CRUD操作
- 💼 **持仓** - 持仓查询和操作
- 🤖 **AI分析** - 交易分析

### 3. API端点列表
每个API端点显示：
- **HTTP方法** (GET/POST/PUT/DELETE)
- **路径** (/api/auth/register)
- **描述** (简要说明)
- **🔓/🔒图标** (是否需要认证)

## 🔑 认证设置（重要！）

大部分API需要JWT Token认证，设置步骤如下：

### 步骤1: 注册或登录获取Token

1. 找到 **认证** 分组下的 `/api/auth/register` 或 `/api/auth/login`
2. 点击展开API详情
3. 点击 **Try it out** 按钮
4. 填写请求参数：
   ```json
   {
     "username": "testuser",
     "email": "test@example.com",
     "password": "password123"
   }
   ```
5. 点击 **Execute** 执行请求
6. 在响应中找到 `token` 字段，复制整个token值

### 步骤2: 设置认证Token

1. 点击页面右上角的 **🔓 Authorize** 按钮
2. 在弹出的对话框中：
   - **Value** 输入框输入: `Bearer <你的token>`
   - 注意：Bearer后面**必须有一个空格**，然后粘贴token
   - 示例: `Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
3. 点击 **Authorize** 按钮
4. 点击 **Close** 关闭对话框
5. 现在所有需要认证的API都会自动带上这个token

### 步骤3: 验证认证

设置完成后，你会看到：
- 🔓 图标变成 🔒（表示已认证）
- 所有需要认证的API都可以直接测试了

## 🧪 测试API步骤

### 示例：测试"获取用户信息"API

1. **找到API端点**
   - 展开 **👤 用户** 分组
   - 找到 `GET /api/user/profile`

2. **查看API详情**
   - 查看 **Description** 了解API功能
   - 查看 **Parameters** 了解参数
   - 查看 **Responses** 了解可能的响应

3. **执行请求**
   - 点击 **Try it out** 按钮
   - 点击 **Execute** 执行请求

4. **查看响应**
   - **Response body**: 返回的JSON数据
   - **Response headers**: HTTP响应头
   - **Status code**: HTTP状态码（200表示成功）

## 📝 常用API测试示例

### 1. 用户注册

```http
POST /api/auth/register
Content-Type: application/json

{
  "username": "trader001",
  "email": "trader@example.com",
  "password": "password123"
}
```

**响应示例**:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "username": "trader001",
    "email": "trader@example.com",
    "created_at": "2024-01-11T10:00:00"
  }
}
```

### 2. 用户登录

```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "trader001",
  "password": "password123"
}
```

### 3. 获取用户信息（需要认证）

```http
GET /api/user/profile
Authorization: Bearer <token>
```

### 4. 创建交易记录（需要认证）

```http
POST /api/trades
Authorization: Bearer <token>
Content-Type: application/json

{
  "stock_code": "600879",
  "stock_name": "航空电子",
  "shares": 1000,
  "buy_price": 15.50,
  "stop_loss_price": 14.00,
  "take_profit_price": 18.00,
  "stop_loss_alert": true,
  "take_profit_alert": true
}
```

### 5. 获取持仓列表（需要认证）

```http
GET /api/positions
Authorization: Bearer <token>
```

### 6. AI分析（需要认证）

```http
GET /api/analysis
Authorization: Bearer <token>
```

## 🎨 Swagger UI 功能说明

### Try it out 模式
- 点击 **Try it out** 后，可以编辑参数并执行请求
- 再次点击可以退出编辑模式

### 参数说明
- **Required**: 红色星号(*)表示必填参数
- **Schema**: 点击查看参数的数据结构
- **Example**: 查看示例值

### 响应说明
- **200**: 成功响应
- **400**: 请求参数错误
- **401**: 未认证或Token无效
- **404**: 资源不存在
- **500**: 服务器错误

### Schema 模型
点击 **Schema** 可以查看：
- 请求参数的数据结构
- 响应数据的数据结构
- 字段类型和说明
- 示例值

## 🔍 搜索功能

Swagger UI 顶部有搜索框，可以：
- 搜索API路径: 输入 `/api/auth`
- 搜索API描述: 输入 "登录"
- 快速定位到需要的API

## 📱 响应式设计

Swagger UI 支持移动端访问：
- 在手机上打开 http://localhost:3000/docs
- 可以查看和测试API（需要先设置认证）

## 🐛 常见问题

### Q1: 为什么有些API显示 🔒 但无法执行？
**A**: 需要先设置认证Token，参考上面的"认证设置"步骤。

### Q2: Token在哪里获取？
**A**: 通过 `/api/auth/register` 或 `/api/auth/login` 接口获取。

### Q3: Token格式是什么？
**A**: 在Authorize对话框中输入: `Bearer <token>`，注意Bearer后面必须有空格。

### Q4: Token过期了怎么办？
**A**: Token有效期为7天，过期后重新登录获取新Token。

### Q5: 如何清除认证？
**A**: 点击右上角的 **Authorize** 按钮，然后点击 **Logout**。

### Q6: 如何查看完整的请求和响应？
**A**: 执行请求后，在响应区域可以看到：
- **Request URL**: 完整的请求URL
- **Request headers**: 请求头（包括Authorization）
- **Response body**: 响应体
- **Response headers**: 响应头

## 💡 使用技巧

### 技巧1: 保存常用请求
- 复制请求的cURL命令
- 在终端中使用或保存到文件

### 技巧2: 批量测试
- 先注册/登录获取Token
- 设置认证
- 依次测试各个API

### 技巧3: 查看Schema
- 点击 **Schema** 查看数据结构
- 点击 **Example** 查看示例值
- 参考示例填写请求参数

### 技巧4: 错误调试
- 查看 **Response body** 中的错误信息
- 查看 **Status code** 了解错误类型
- 检查请求参数是否正确

## 📊 API测试流程建议

### 完整测试流程

1. **注册用户**
   ```
   POST /api/auth/register
   → 获取token
   ```

2. **设置认证**
   ```
   点击Authorize → 输入Bearer <token>
   ```

3. **查看用户信息**
   ```
   GET /api/user/profile
   ```

4. **更新资金**
   ```
   POST /api/user/capital
   ```

5. **创建交易记录**
   ```
   POST /api/trades
   ```

6. **查看持仓**
   ```
   GET /api/positions
   ```

7. **执行止盈**
   ```
   POST /api/positions/{id}/take-profit
   ```

8. **查看AI分析**
   ```
   GET /api/analysis
   ```

## 🎯 快速开始示例

### 第一次使用

1. 打开 http://localhost:3000/docs
2. 找到 **POST /api/auth/register**
3. 点击 **Try it out**
4. 填写注册信息：
   ```json
   {
     "username": "myuser",
     "email": "my@email.com",
     "password": "mypassword"
   }
   ```
5. 点击 **Execute**
6. 复制返回的 `token`
7. 点击右上角 **Authorize**
8. 输入 `Bearer <粘贴token>`
9. 点击 **Authorize** → **Close**
10. 现在可以测试所有需要认证的API了！

## 📚 相关文档

- **DEBUG_GUIDE.md**: 日志调试指南
- **README.md**: 项目说明文档
- **ReDoc**: http://localhost:3000/redoc (另一种文档格式)

## 🎉 总结

Swagger UI 是一个非常强大的工具，可以：
- ✅ 无需编写代码即可测试API
- ✅ 查看完整的API文档
- ✅ 理解API的使用方式
- ✅ 快速调试和验证功能

开始使用 Swagger UI，让API测试变得简单高效！
