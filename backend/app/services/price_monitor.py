from typing import Dict, Set, Optional
import asyncio
from datetime import datetime
import aiohttp
import logging
import json

logger = logging.getLogger(__name__)

class PriceMonitor:
    def __init__(self):
        self.subscriptions: Dict[str, Set[str]] = {}  # socket_id -> stock_codes
        self.price_cache: Dict[str, tuple[float, datetime, str]] = {}  # (价格, 时间戳, 来源)
        self.running = False
        self.task: asyncio.Task | None = None
        self.CACHE_TTL = 30  # 30秒缓存（A股交易时间可以更频繁）
        self.update_interval = 5  # 5秒更新一次价格
    
    def _normalize_stock_code(self, stock_code: str) -> str:
        """标准化股票代码格式
        A股代码格式：
        - 上海：600xxx, 601xxx, 603xxx, 605xxx -> sh600xxx
        - 深圳：000xxx, 001xxx, 002xxx, 003xxx -> sz000xxx
        - 创业板：300xxx -> sz300xxx
        - 科创板：688xxx -> sh688xxx
        """
        code = stock_code.strip()
        
        # 如果已经是标准格式（带sh/sz前缀），直接返回
        if code.startswith('sh') or code.startswith('sz'):
            return code.lower()
        
        # 转换为数字部分
        try:
            num_code = int(code)
        except ValueError:
            return code
        
        # 判断市场
        if num_code >= 600000 and num_code < 700000:
            return f"sh{code}"
        elif num_code >= 300000 and num_code < 400000:
            return f"sz{code}"
        elif num_code >= 000000 and num_code < 300000:
            return f"sz{code.zfill(6)}"
        else:
            return code
    
    async def fetch_stock_price_sina(self, stock_code: str) -> tuple[Optional[float], str]:
        """使用新浪财经API获取A股价格（免费）
        返回: (价格, 来源)"""
        try:
            normalized_code = self._normalize_stock_code(stock_code)
            url = f"http://hq.sinajs.cn/list={normalized_code}"
            
            # 使用HTTP连接器，避免SSL问题
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        # 新浪API返回格式：var hq_str_sh600879="航天电子,15.50,15.60,..."
                        if text and '=' in text:
                            data_str = text.split('=')[1].strip().strip('"')
                            if data_str and ',' in data_str:
                                parts = data_str.split(',')
                                if len(parts) >= 3:
                                    # parts[3] 是当前价格
                                    price = float(parts[3])
                                    return (round(price, 2), "新浪财经")
            return (None, "新浪财经")
        except Exception as e:
            logger.error(f"从新浪API获取股票 {stock_code} 价格失败: {e}")
            return (None, "新浪财经")
    
    async def fetch_stock_price_tencent(self, stock_code: str) -> tuple[Optional[float], str]:
        """使用腾讯财经API获取A股价格（备用方案）
        返回: (价格, 来源)"""
        try:
            normalized_code = self._normalize_stock_code(stock_code)
            # 腾讯API格式：使用HTTP避免SSL证书问题
            url = f"http://qt.gtimg.cn/q={normalized_code}"
            
            # 使用HTTP连接器，避免SSL问题
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        # 腾讯API返回格式：v_sh600879="航天电子~15.50~15.60~..."
                        if text and '=' in text:
                            data_str = text.split('=')[1].strip().strip('"')
                            if data_str and '~' in data_str:
                                parts = data_str.split('~')
                                if len(parts) >= 3:
                                    # parts[3] 是当前价格
                                    price = float(parts[3])
                                    return (round(price, 2), "腾讯财经")
            return (None, "腾讯财经")
        except Exception as e:
            logger.error(f"从腾讯API获取股票 {stock_code} 价格失败: {e}")
            return (None, "腾讯财经")
    
    async def fetch_stock_price(self, stock_code: str) -> tuple[float, str]:
        """获取股票价格（带缓存和重试机制）
        返回: (价格, 来源)"""
        # 检查缓存
        if stock_code in self.price_cache:
            price_data = self.price_cache[stock_code]
            if isinstance(price_data, tuple) and len(price_data) >= 3:
                price, timestamp, source = price_data
                if (datetime.utcnow() - timestamp).seconds < self.CACHE_TTL:
                    return (price, source)
        
        # 尝试从新浪API获取
        price, source = await self.fetch_stock_price_sina(stock_code)
        
        # 如果失败，尝试腾讯API
        if price is None:
            price, source = await self.fetch_stock_price_tencent(stock_code)
        
        # 如果都失败，使用缓存或返回0
        if price is None:
            if stock_code in self.price_cache:
                price_data = self.price_cache[stock_code]
                if isinstance(price_data, tuple) and len(price_data) >= 3:
                    cached_price, _, cached_source = price_data
                    logger.warning(f"获取股票 {stock_code} 价格失败，使用缓存价格")
                    return (cached_price, cached_source + "(缓存)")
            logger.warning(f"获取股票 {stock_code} 价格失败，返回0")
            return (0.0, "获取失败")
        
        # 更新缓存 (价格, 时间戳, 来源)
        self.price_cache[stock_code] = (price, datetime.utcnow(), source)
        logger.info(f"获取股票 {stock_code} 价格: {price} (来源: {source})")
        return (price, source)
    
    async def batch_fetch_prices(self, stock_codes: list[str]) -> Dict[str, Dict[str, any]]:
        """批量获取股票价格
        返回: {stock_code: {"price": float, "source": str}}"""
        prices = {}
        tasks = [self.fetch_stock_price(code) for code in stock_codes]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for code, result in zip(stock_codes, results):
            if isinstance(result, Exception):
                logger.error(f"获取股票 {code} 价格异常: {result}")
                cached_data = self.price_cache.get(code, (0.0, datetime.utcnow(), "缓存"))
                prices[code] = {
                    "price": cached_data[0] if isinstance(cached_data, tuple) else 0.0,
                    "source": cached_data[2] if isinstance(cached_data, tuple) and len(cached_data) >= 3 else "获取失败"
                }
            else:
                price, source = result
                prices[code] = {"price": price, "source": source}
        
        return prices
    
    def get_current_price(self, stock_code: str) -> tuple[Optional[float], Optional[str]]:
        """获取当前缓存的价格和来源（同步方法）
        返回: (价格, 来源)"""
        if stock_code in self.price_cache:
            price_data = self.price_cache[stock_code]
            if isinstance(price_data, tuple) and len(price_data) >= 3:
                return (price_data[0], price_data[2])
            elif isinstance(price_data, tuple) and len(price_data) >= 2:
                return (price_data[0], "缓存")
        return (None, None)
    
    def subscribe(self, socket_id: str, stock_codes: list[str]):
        """订阅股票价格更新"""
        self.subscriptions[socket_id] = set(stock_codes)
        logger.info(f"订阅价格更新: {socket_id} -> {stock_codes}")
    
    def unsubscribe(self, socket_id: str):
        """取消订阅"""
        if socket_id in self.subscriptions:
            del self.subscriptions[socket_id]
            logger.info(f"取消订阅: {socket_id}")
    
    async def update_prices_loop(self):
        """价格更新循环"""
        while self.running:
            try:
                # 收集所有需要监控的股票代码
                all_stock_codes = set()
                for stock_codes in self.subscriptions.values():
                    all_stock_codes.update(stock_codes)
                
                if all_stock_codes:
                    # 批量获取价格
                    prices = await self.batch_fetch_prices(list(all_stock_codes))
                    logger.debug(f"更新价格: {prices}")
                
                await asyncio.sleep(self.update_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"价格更新循环错误: {e}")
                await asyncio.sleep(self.update_interval)
    
    async def start(self):
        """启动价格监控服务"""
        if self.running:
            return
        
        self.running = True
        self.task = asyncio.create_task(self.update_prices_loop())
        logger.info("价格监控服务已启动")
    
    async def stop(self):
        """停止价格监控服务"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("价格监控服务已停止")

# 全局实例
price_monitor = PriceMonitor()
