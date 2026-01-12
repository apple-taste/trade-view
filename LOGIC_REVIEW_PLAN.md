# 逻辑审查计划

## 📋 审查目标
确保系统各模块逻辑通畅，数据流正确，用户体验良好。

---

## 1. 数据流审查

### 1.1 交易记录创建流程
- [ ] **前端 → 后端**
  - [ ] `TradeHistoryPanel` 表单提交 → `POST /api/trades`
  - [ ] 数据验证：股票代码、价格、股数等必填字段
  - [ ] 日期格式转换：`datetime-local` → ISO 8601

- [ ] **后端处理**
  - [ ] `TradeCreate` 模型验证
  - [ ] 数据库插入：`Trade` 表
  - [ ] 默认值设置：`status="open"`, `open_time=now()`

- [ ] **数据同步**
  - [ ] 创建后触发 `refreshCalendar()` - 更新日历标记
  - [ ] 创建后触发 `refreshPositions()` - 更新持仓列表
  - [ ] 创建后触发 `refreshAnalysis()` - 更新AI分析
  - [ ] 创建后触发 `refreshUserPanel()` - 更新资金（如果有变化）

### 1.2 持仓操作流程
- [ ] **止盈/止损操作**
  - [ ] `PositionPanel` 点击止盈/止损 → `POST /api/positions/{id}/take-profit` 或 `/stop-loss`
  - [ ] 后端更新：`status="closed"`, `order_result="止盈"/"止损"`, `sell_price`, `close_time`
  - [ ] 触发刷新：日历、分析、用户面板

- [ ] **闹铃切换**
  - [ ] 点击闹铃图标 → `PUT /api/positions/{id}`
  - [ ] 更新 `stop_loss_alert` 或 `take_profit_alert`
  - [ ] 前端状态同步更新

### 1.3 价格更新流程
- [ ] **自动刷新**
  - [ ] `PositionPanel` 每5秒调用 `refreshPrices()`
  - [ ] `POST /api/price/batch` 批量获取价格
  - [ ] `price_monitor.batch_fetch_prices()` 处理
  - [ ] 返回价格和来源（新浪财经/腾讯财经）
  - [ ] 前端更新 `current_price` 和 `price_source`
  - [ ] 检查闹铃触发条件

- [ ] **价格来源追踪**
  - [ ] `fetch_stock_price_sina()` 返回 `(价格, "新浪财经")`
  - [ ] `fetch_stock_price_tencent()` 返回 `(价格, "腾讯财经")`
  - [ ] 缓存包含来源信息：`(价格, 时间戳, 来源)`
  - [ ] API响应包含 `price_source` 字段

---

## 2. 面板间交互审查

### 2.1 TradeContext 机制
- [ ] **Context 提供者**
  - [ ] `App.tsx` 中正确包裹 `TradeProvider`
  - [ ] `TradeContext` 提供刷新函数和 refresh keys

- [ ] **刷新触发**
  - [ ] `TradeHistoryPanel`: 创建/更新/删除交易后调用刷新函数
  - [ ] `PositionPanel`: 止盈/止损后调用刷新函数
  - [ ] 各面板监听对应的 `_refreshKey` 变化

- [ ] **刷新响应**
  - [ ] `CalendarPanel`: `useEffect([_calendarRefreshKey])` 重新获取交易日期
  - [ ] `AnalysisPanel`: `useEffect([_analysisRefreshKey])` 重新获取分析数据
  - [ ] `UserPanel`: `useEffect([_userPanelRefreshKey])` 重新获取资金数据
  - [ ] `PositionPanel`: `useEffect([_positionsRefreshKey])` 重新获取持仓

### 2.2 日历与交易历史联动
- [ ] **日期选择**
  - [ ] 点击日历日期 → `onDateChange(date)` → `setSelectedDate(date)`
  - [ ] `TradeHistoryPanel` 监听 `selectedDate` 变化
  - [ ] 自动调用 `fetchTrades()` 获取该日期交易记录

- [ ] **交易标记**
  - [ ] `CalendarPanel` 获取 `/api/trades/dates` 获取有交易的日期
  - [ ] 有交易的日期显示 📈 表情
  - [ ] 创建/删除交易后刷新标记

---

## 3. API 端点审查

### 3.1 交易记录 API (`/api/trades`)
- [ ] `GET /api/trades` - 获取所有交易记录
- [ ] `GET /api/trades/date/{date}` - 按日期获取交易记录
- [ ] `GET /api/trades/dates` - 获取有交易的日期列表
- [ ] `POST /api/trades` - 创建交易记录
- [ ] `PUT /api/trades/{id}` - 更新交易记录
- [ ] `DELETE /api/trades/{id}` - 删除交易记录

### 3.2 持仓 API (`/api/positions`)
- [ ] `GET /api/positions` - 获取所有持仓（包含价格和来源）
- [ ] `PUT /api/positions/{id}` - 更新持仓（闹铃设置等）
- [ ] `POST /api/positions/{id}/take-profit` - 执行止盈
- [ ] `POST /api/positions/{id}/stop-loss` - 执行止损

### 3.3 价格 API (`/api/price`)
- [ ] `GET /api/price/{stock_code}` - 获取单个股票价格（含来源）
- [ ] `POST /api/price/batch` - 批量获取价格（含来源）

### 3.4 用户 API (`/api/user`)
- [ ] `GET /api/user/capital` - 获取当前资金
- [ ] `POST /api/user/capital` - 更新资金
- [ ] `GET /api/user/capital-history` - 获取资金历史

### 3.5 AI分析 API (`/api/analysis`)
- [ ] `GET /api/analysis/trade-summary` - 获取AI分析结果

---

## 4. 价格监控逻辑审查

### 4.1 价格获取策略
- [ ] **优先级**
  - [ ] 先检查缓存（30秒TTL）
  - [ ] 缓存未命中 → 尝试新浪财经API
  - [ ] 新浪失败 → 尝试腾讯财经API
  - [ ] 都失败 → 返回缓存价格或0.0

- [ ] **缓存机制**
  - [ ] 缓存结构：`(价格, 时间戳, 来源)`
  - [ ] TTL检查：`(now - timestamp).seconds < 30`
  - [ ] 缓存更新：每次成功获取后更新

### 4.2 股票代码标准化
- [ ] **市场判断**
  - [ ] 600xxx, 601xxx, 603xxx, 605xxx, 688xxx → `sh` (上海)
  - [ ] 000xxx, 001xxx, 002xxx, 003xxx, 300xxx → `sz` (深圳)
  - [ ] 已带前缀的代码直接使用

### 4.3 批量获取优化
- [ ] **并发处理**
  - [ ] `asyncio.gather()` 并发获取多个股票价格
  - [ ] 异常处理：单个股票失败不影响其他
  - [ ] 返回格式：`{stock_code: {"price": float, "source": str}}`

---

## 5. 闹铃逻辑审查

### 5.1 闹铃触发条件
- [ ] **止损提醒**
  - [ ] `stop_loss_alert == True`
  - [ ] `stop_loss_price` 已设置
  - [ ] `current_price <= stop_loss_price`
  - [ ] 触发 `alert()` 提示

- [ ] **止盈提醒**
  - [ ] `take_profit_alert == True`
  - [ ] `take_profit_price` 已设置
  - [ ] `current_price >= take_profit_price`
  - [ ] 触发 `alert()` 提示

### 5.2 闹铃检查时机
- [ ] **初始加载**
  - [ ] `fetchPositions()` 后检查所有持仓

- [ ] **价格更新**
  - [ ] `refreshPrices()` 更新价格后检查
  - [ ] 避免重复提醒（需要状态管理）

---

## 6. 错误处理审查

### 6.1 前端错误处理
- [ ] **API请求失败**
  - [ ] `try-catch` 包裹所有 `axios` 请求
  - [ ] 显示用户友好的错误信息
  - [ ] 网络错误时提示重试

- [ ] **数据验证**
  - [ ] 表单必填字段验证
  - [ ] 数字格式验证（价格、股数）
  - [ ] 日期格式验证

### 6.2 后端错误处理
- [ ] **HTTP异常**
  - [ ] `HTTPException` 用于业务错误（404, 400等）
  - [ ] 错误信息清晰明确

- [ ] **数据库错误**
  - [ ] 唯一约束冲突处理（用户名、邮箱重复）
  - [ ] 外键约束错误处理
  - [ ] 事务回滚机制

- [ ] **价格获取失败**
  - [ ] 网络超时处理（5秒超时）
  - [ ] API返回格式错误处理
  - [ ] 降级策略：使用缓存或返回0.0

---

## 7. 状态同步审查

### 7.1 持仓状态
- [ ] **状态转换**
  - [ ] `open` → `closed`（止盈/止损时）
  - [ ] 状态变更后从持仓列表移除
  - [ ] 交易历史中保留记录

### 7.2 交易记录状态
- [ ] **创建时**
  - [ ] `status = "open"`
  - [ ] `order_result = None`

- [ ] **平仓时**
  - [ ] `status = "closed"`
  - [ ] `order_result = "止盈"` 或 `"止损"`
  - [ ] `sell_price` 和 `close_time` 设置

### 7.3 资金状态
- [ ] **资金更新**
  - [ ] 止盈/止损后可能需要更新资金
  - [ ] 资金历史记录创建

---

## 8. AI分析逻辑审查

### 8.1 数据准备
- [ ] **交易数据筛选**
  - [ ] 只分析 `status="closed"` 的交易
  - [ ] 必须有 `sell_price`

- [ ] **统计数据计算**
  - [ ] 总交易次数、胜率、累计盈亏
  - [ ] 平均持仓天数
  - [ ] 止损/止盈执行次数
  - [ ] 盈亏比计算

### 8.2 AI分析调用
- [ ] **MCP ChatGPT集成**
  - [ ] `AI_BUILDER_TOKEN` 环境变量设置
  - [ ] API调用：`https://space.ai-builders.com/backend/v1/chat/completions`
  - [ ] 模型：`gpt-5`
  - [ ] 温度：`1.0`（gpt-5要求）
  - [ ] `max_completion_tokens`: 3000

- [ ] **Prompt构建**
  - [ ] 包含交易统计数据
  - [ ] 包含资金历史数据（如果有）
  - [ ] 明确要求分析止损止盈、入场价格、盈亏比、资金管理

- [ ] **响应解析**
  - [ ] JSON格式解析
  - [ ] 提取 `stop_loss_analysis`, `take_profit_analysis` 等字段
  - [ ] 解析失败时使用基础分析

---

## 9. 用户体验审查

### 9.1 加载状态
- [ ] **Loading指示**
  - [ ] 各面板加载时显示加载动画
  - [ ] 价格刷新时显示刷新状态

### 9.2 反馈提示
- [ ] **操作成功**
  - [ ] 创建/更新/删除交易后提示
  - [ ] 止盈/止损操作后提示

- [ ] **操作失败**
  - [ ] 显示具体错误信息
  - [ ] 提供重试建议

### 9.3 数据展示
- [ ] **价格显示**
  - [ ] 当前市价突出显示
  - [ ] 价格来源清晰标注
  - [ ] 盈亏用颜色区分（绿色/红色）

- [ ] **闹铃状态**
  - [ ] 开启时高亮显示
  - [ ] 图标动画效果
  - [ ] "提醒已开启"文字提示

---

## 10. 性能审查

### 10.1 价格刷新
- [ ] **刷新频率**
  - [ ] 自动刷新：每5秒
  - [ ] 手动刷新：用户点击按钮
  - [ ] 避免过度请求

- [ ] **批量处理**
  - [ ] 批量获取价格而非逐个请求
  - [ ] 并发处理多个股票

### 10.2 数据缓存
- [ ] **价格缓存**
  - [ ] 30秒TTL避免频繁请求
  - [ ] 缓存包含来源信息

- [ ] **前端缓存**
  - [ ] React状态管理避免重复请求
  - [ ] refresh key机制控制刷新时机

---

## 🔍 审查方法

### 方法1: 代码审查
1. 按照上述清单逐项检查代码
2. 重点关注数据流和状态管理
3. 检查错误处理是否完善

### 方法2: 功能测试
1. **交易流程测试**
   - 创建交易 → 检查日历标记 → 检查持仓列表 → 检查AI分析
   
2. **持仓操作测试**
   - 设置止损止盈 → 开启闹铃 → 等待价格触发 → 执行止盈/止损
   
3. **价格更新测试**
   - 观察价格刷新 → 检查价格来源显示 → 验证闹铃触发

### 方法3: 日志分析
1. 查看后端日志：`backend/backend.log`
2. 查看前端控制台日志
3. 检查API请求和响应

### 方法4: 端到端测试场景
1. **完整交易流程**
   ```
   用户登录 → 添加交易记录 → 查看持仓 → 
   设置止损止盈 → 开启闹铃 → 价格触发提醒 → 
   执行止盈 → 查看交易历史 → 查看AI分析
   ```

2. **多日期交易**
   ```
   在不同日期添加交易 → 切换日历日期 → 
   查看对应日期的交易记录 → 查看全部历史
   ```

---

## 📝 审查检查表

### 关键路径检查
- [ ] 创建交易 → 日历标记更新 ✓
- [ ] 创建交易 → 持仓列表更新 ✓
- [ ] 止盈/止损 → 交易状态更新 ✓
- [ ] 止盈/止损 → 持仓列表移除 ✓
- [ ] 价格更新 → 闹铃触发检查 ✓
- [ ] 价格更新 → 价格来源显示 ✓

### 边界情况检查
- [ ] 无交易记录时的显示
- [ ] 无持仓时的显示
- [ ] 价格获取失败时的处理
- [ ] 网络错误时的处理
- [ ] AI分析失败时的降级

### 数据一致性检查
- [ ] 持仓列表与交易记录一致
- [ ] 日历标记与实际交易一致
- [ ] 资金数据与交易记录一致
- [ ] AI分析数据与交易记录一致

---

## 🚀 下一步行动

1. **立即检查**（高优先级）
   - [ ] TradeContext刷新机制是否正确
   - [ ] 价格来源是否正确返回和显示
   - [ ] 闹铃触发逻辑是否正确

2. **功能测试**（中优先级）
   - [ ] 完整交易流程测试
   - [ ] 多面板联动测试
   - [ ] 错误场景测试

3. **优化改进**（低优先级）
   - [ ] 性能优化（如果需要）
   - [ ] UI/UX改进
   - [ ] 错误提示优化

---

## 📚 相关文档

- `DEBUG_GUIDE.md` - 调试指南
- `SWAGGER_UI_GUIDE.md` - API测试指南
- `STATUS_CHECK.md` - 状态检查方法

---

**审查完成后，请更新此文档，标记已完成的项目。**
