# 资金计算修复说明

## 修复日期：2026-01-12

---

## ❌ 发现的问题

用户反馈：买1股2元，卖5元，手续费5元，应该是亏7元，但系统计算不正确。

### 问题根源

**旧代码的错误逻辑**（已修复）：
```python
# ❌ 错误：平仓时的资金变化计算
capital_recovery = buy_price × shares + buy_commission  # 本金回收
capital_change = capital_recovery + profit_loss
await update_capital_from_trade(db, user_id, capital_change, date)
```

**问题**：
1. 开仓时已经扣除了资金：`可用资金 -= (buy_price × shares + buy_commission)`
2. 平仓时又加回 `capital_recovery`，导致**重复计算**
3. 相当于把开仓扣的钱退回来，再加上盈亏

---

## ✅ 正确的逻辑

### 同花顺资金管理模式

```python
# 开仓时
可用资金 -= (buy_price × shares + buy_commission)
持仓增加

# 平仓时  
可用资金 += (sell_price × shares - sell_commission)
持仓减少

# 净盈亏自动反映在资金变化中
```

### 用户例子验证

```
初始资金: 100元

开仓：买1股2元 + 手续费5元
├─ 可用资金: 100 - 7 = 93元
├─ 持仓市值: 2元
└─ 总资产: 95元

平仓：卖1股5元 - 手续费5元
├─ 平仓收入: 5 - 5 = 0元
├─ 可用资金: 93 + 0 = 93元
├─ 持仓市值: 0元
└─ 总资产: 93元

净盈亏: 93 - 100 = -7元 ✅
价差收益: 3元
总手续费: 10元
-7元 = 3元 - 10元 ✅
```

---

## 🔧 修复内容

### 1. 移除错误的资金更新逻辑

**修改文件**：`backend/app/routers/positions.py`

**修复前**（止盈）：
```python
position.profit_loss = profit_loss
position.updated_at = close_time

# ❌ 错误的资金更新
capital_recovery = position.buy_price * position.shares + commission
capital_change = capital_recovery + profit_loss
await update_capital_from_trade(db, user_id, capital_change, date)

await db.commit()
```

**修复后**（止盈）：
```python
position.profit_loss = profit_loss
position.updated_at = close_time

# ✅ 直接提交，不再调用 update_capital_from_trade
await db.commit()
await db.refresh(position)

# ✅ 调用 recalculate_capital_history 统一重算整个资金曲线
await recalculate_capital_history(db, user_id, initial_date)
```

**止损操作也同样修复**。

### 2. 废弃 update_capital_from_trade 函数

```python
# 已废弃，改用 recalculate_capital_history 统一重算
async def update_capital_from_trade(...):
    """已废弃：改用 recalculate_capital_history 统一重算"""
    pass
```

### 3. 其他修复

1. **添加离场价格列**（开仓历史记录）
   - 显示用户输入的实际离场价格
   - 绿色：盈利（离场价 > 入场价）
   - 红色：亏损（离场价 < 入场价）

2. **已平仓交易不显示出场闹铃**
   - 只有持仓中才显示止损/止盈闹铃
   - 已平仓显示 `-`

3. **止盈/止损后自动清除闹铃**
   - 调用 `clearAlertsByStockCode`

---

## 📊 资金计算流程

### recalculate_capital_history 函数

```python
# 初始状态
available_funds = initial_capital  # 例：100元
positions = {}

# 处理开仓事件
if event['type'] == 'open':
    cost = trade.buy_price × trade.shares + trade.commission
    available_funds -= cost  # 例：100 - 7 = 93元
    positions[trade.id] = trade

# 处理平仓事件
elif event['type'] == 'close':
    sell_amount = trade.sell_price × trade.shares
    sell_commission = calculate_sell_commission(...)
    available_funds += sell_amount - sell_commission  # 例：93 + 0 = 93元
    del positions[trade.id]

# 计算持仓市值
position_value = Σ(buy_price × shares for each position)

# 计算总资产
total_assets = available_funds + position_value
```

---

## 🎯 关键要点

### 1. 资金流动
```
开仓：资金流出 = 买入价 × 手数 + 买入手续费
平仓：资金流入 = 卖出价 × 手数 - 卖出手续费
```

### 2. 盈亏计算
```
净盈亏 = 资金流入 - 资金流出
      = (卖出价 × 手数 - 卖出手续费) - (买入价 × 手数 + 买入手续费)
      = (卖出价 - 买入价) × 手数 - 总手续费
```

### 3. 不要重复计算
```
❌ 错误：平仓时 += (本金回收 + 盈亏)
✅ 正确：平仓时 += (卖出收入 - 卖出手续费)
```

---

## 📖 测试用例

### 用例1：盈利交易
```
买入：10股 × 10元 + 5元手续费 = 扣105元
卖出：10股 × 12元 - 7元手续费 = 收113元
净盈亏：113 - 105 = +8元 ✅
```

### 用例2：亏损交易（用户例子）
```
买入：1股 × 2元 + 5元手续费 = 扣7元
卖出：1股 × 5元 - 5元手续费 = 收0元
净盈亏：0 - 7 = -7元 ✅
```

### 用例3：持仓中
```
买入：100股 × 15元 + 50元手续费 = 扣1550元
当前：股价涨到16元
可用资金：initial - 1550元
持仓市值：100 × 16 = 1600元（使用当前价）
总资产：可用资金 + 1600元
浮动盈亏：(16 - 15) × 100 - 50 = +50元
```

---

**修复状态**：✅ 已完成
**测试状态**：✅ 需要重启后端验证
