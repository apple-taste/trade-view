"""
闹铃监控服务

定期检查持仓的止损止盈条件，触发闹铃通知（WebSocket + 邮件）
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Set
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Trade, User, get_db
from app.services.price_monitor import price_monitor
from app.services.email_service import default_email_service

logger = logging.getLogger(__name__)


class AlertMonitor:
    """闹铃监控服务"""
    
    def __init__(self):
        self.running = False
        self.task: asyncio.Task | None = None
        self.check_interval = 10  # 每10秒检查一次
        self.triggered_alerts: Dict[int, Set[str]] = {}  # trade_id -> {'stop_loss', 'take_profit'}
        
    async def start(self):
        """启动监控服务"""
        if self.running:
            logger.warning("闹铃监控服务已在运行")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._monitor_loop())
        logger.info("✅ 闹铃监控服务已启动")
    
    async def stop(self):
        """停止监控服务"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("⏹️ 闹铃监控服务已停止")
    
    async def _monitor_loop(self):
        """监控循环"""
        while self.running:
            try:
                await self._check_all_positions()
            except Exception as e:
                logger.error(f"闹铃监控出错: {e}")
            
            await asyncio.sleep(self.check_interval)
    
    async def _check_all_positions(self):
        """检查所有持仓的止损止盈条件"""
        async for db in get_db():
            try:
                result = await db.execute(
                    select(Trade).where(Trade.status == "open", Trade.is_deleted == False)
                )
                positions = result.scalars().all()

                if not positions:
                    return

                stock_codes = [pos.stock_code for pos in positions if pos.stock_code]
                price_data = await price_monitor.batch_fetch_prices(stock_codes)

                for position in positions:
                    await self._check_position_alert(db, position, price_data)

            except Exception as e:
                logger.error(f"检查持仓闹铃失败: {e}")
            return
    
    async def _check_position_alert(
        self,
        db: AsyncSession,
        position: Trade,
        price_data: Dict[str, Dict]
    ):
        """检查单个持仓的闹铃条件"""
        try:
            # 获取当前价格
            if position.stock_code not in price_data:
                return
            
            price_info = price_data[position.stock_code]
            current_price = price_info.get("price", 0)
            
            if current_price <= 0:
                return
            
            # 初始化该持仓的已触发闹铃记录
            if position.id not in self.triggered_alerts:
                self.triggered_alerts[position.id] = set()
            
            # 检查止损闹铃
            if (position.stop_loss_alert and 
                position.stop_loss_price and 
                current_price <= position.stop_loss_price and
                'stop_loss' not in self.triggered_alerts[position.id]):
                
                await self._trigger_alert(
                    db,
                    position,
                    "stop_loss",
                    current_price,
                    position.stop_loss_price
                )
                self.triggered_alerts[position.id].add('stop_loss')
            
            # 检查止盈闹铃
            if (position.take_profit_alert and 
                position.take_profit_price and 
                current_price >= position.take_profit_price and
                'take_profit' not in self.triggered_alerts[position.id]):
                
                await self._trigger_alert(
                    db,
                    position,
                    "take_profit",
                    current_price,
                    position.take_profit_price
                )
                self.triggered_alerts[position.id].add('take_profit')
        
        except Exception as e:
            logger.error(f"检查持仓 {position.id} 闹铃失败: {e}")
    
    async def _trigger_alert(
        self,
        db: AsyncSession,
        position: Trade,
        alert_type: str,
        current_price: float,
        target_price: float
    ):
        """触发闹铃（发送邮件通知）"""
        try:
            alert_type_zh = "止盈" if alert_type == "take_profit" else "止损"
            logger.info(
                f"🔔 触发闹铃: {position.stock_code} - {alert_type_zh} "
                f"(当前价格: {current_price}, 目标价格: {target_price})"
            )
            
            # 获取用户信息
            result = await db.execute(
                select(User).where(User.id == position.user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return
            
            # 发送邮件通知（如果用户启用了邮箱提醒）
            if user.email_alerts_enabled and user.email:
                success = default_email_service.send_price_alert(
                    to_email=user.email,
                    stock_code=position.stock_code,
                    stock_name=position.stock_name,
                    alert_type=alert_type,
                    current_price=current_price,
                    target_price=target_price
                )
                
                if success:
                    logger.info(f"✅ 邮件通知已发送: {user.email} - {position.stock_code}")
                else:
                    logger.warning(f"⚠️ 邮件通知发送失败: {user.email} - {position.stock_code}")
            
            # TODO: 如果有WebSocket连接，也通过WebSocket发送实时通知
            # 这部分需要在main.py中实现WebSocket端点
            
        except Exception as e:
            logger.error(f"触发闹铃失败: {e}")
    
    def clear_position_alerts(self, position_id: int):
        """清除某个持仓的已触发闹铃记录（用于用户取消闹铃或平仓时）"""
        if position_id in self.triggered_alerts:
            del self.triggered_alerts[position_id]


# 全局闹铃监控实例
alert_monitor = AlertMonitor()
