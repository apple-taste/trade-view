"""
中信证券华南手续费计算服务

手续费组成：
1. 佣金：0.02%-0.3%（可协商），最低5元
2. 印花税：仅在卖出时收取，按成交金额的0.1%
3. 过户费：仅上海股票（6开头）收取，按成交金额的0.02%，深圳股票（0、3开头）不收取

计算公式：
- 买入手续费 = 佣金（成交金额 * 佣金率，最低5元）
- 卖出手续费 = 佣金（成交金额 * 佣金率，最低5元）+ 印花税（成交金额 * 0.1%）+ 过户费（仅上海股票，成交金额 * 0.02%）
"""

from typing import Optional


class CommissionCalculator:
    """手续费计算器"""
    
    def __init__(self, commission_rate: float = 0.0003, min_commission: float = 5.0):
        """
        初始化手续费计算器
        
        Args:
            commission_rate: 佣金费率（默认0.03%，即0.0003）
            min_commission: 最低佣金（默认5元）
        """
        self.commission_rate = commission_rate  # 佣金费率（例如：0.0003 表示 0.03%）
        self.min_commission = min_commission  # 最低佣金（元）
    
    def calculate_buy_commission(self, price: float, shares: int) -> float:
        """
        计算买入手续费
        
        Args:
            price: 买入价格
            shares: 买入股数
            
        Returns:
            手续费金额（元）
        """
        trade_amount = price * shares  # 成交金额
        commission = trade_amount * self.commission_rate  # 佣金
        
        # 佣金不足最低标准时，按最低标准收取
        if commission < self.min_commission:
            commission = self.min_commission
        
        return round(commission, 2)
    
    def calculate_sell_commission(self, price: float, shares: int, stock_code: str) -> float:
        """
        计算卖出手续费
        
        Args:
            price: 卖出价格
            shares: 卖出股数
            stock_code: 股票代码（用于判断是否为上海股票）
            
        Returns:
            手续费金额（元）
        """
        trade_amount = price * shares  # 成交金额
        
        # 1. 佣金
        commission = trade_amount * self.commission_rate
        if commission < self.min_commission:
            commission = self.min_commission
        
        # 2. 印花税（卖出时收取，0.1%）
        stamp_tax = trade_amount * 0.001
        
        # 3. 过户费（仅上海股票，6开头）
        transfer_fee = 0.0
        if stock_code.startswith('6'):
            transfer_fee = trade_amount * 0.0002  # 0.02%
        
        total_commission = commission + stamp_tax + transfer_fee
        return round(total_commission, 2)
    
    def calculate_total_commission(self, buy_price: float, sell_price: float, shares: int, stock_code: str) -> float:
        """
        计算总手续费（买入 + 卖出）
        
        Args:
            buy_price: 买入价格
            sell_price: 卖出价格
            shares: 股数
            stock_code: 股票代码
            
        Returns:
            总手续费金额（元）
        """
        buy_comm = self.calculate_buy_commission(buy_price, shares)
        sell_comm = self.calculate_sell_commission(sell_price, shares, stock_code)
        return round(buy_comm + sell_comm, 2)


# 默认手续费计算器实例（使用默认参数：0.03%佣金率，最低5元）
default_calculator = CommissionCalculator(commission_rate=0.0003, min_commission=5.0)
