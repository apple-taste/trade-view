from typing import Dict, Set, Optional
import asyncio
from datetime import datetime
import aiohttp
import logging
import json
import time

logger = logging.getLogger(__name__)

# API性能统计
class APIPerformance:
    def __init__(self):
        self.stats: Dict[str, Dict] = {}  # {api_name: {count, total_time, avg_time, success_count, fail_count}}
    
    def record(self, api_name: str, response_time: float, success: bool):
        """记录API调用性能"""
        if api_name not in self.stats:
            self.stats[api_name] = {
                'count': 0,
                'total_time': 0.0,
                'avg_time': 0.0,
                'success_count': 0,
                'fail_count': 0,
                'min_time': float('inf'),
                'max_time': 0.0
            }
        
        stats = self.stats[api_name]
        stats['count'] += 1
        stats['total_time'] += response_time
        stats['avg_time'] = stats['total_time'] / stats['count']
        stats['min_time'] = min(stats['min_time'], response_time)
        stats['max_time'] = max(stats['max_time'], response_time)
        
        if success:
            stats['success_count'] += 1
        else:
            stats['fail_count'] += 1
    
    def get_best_api(self) -> Optional[str]:
        """获取平均响应时间最短的API"""
        if not self.stats:
            return None
        
        best_api = None
        best_avg_time = float('inf')
        
        for api_name, stats in self.stats.items():
            if stats['success_count'] > 0 and stats['avg_time'] < best_avg_time:
                best_avg_time = stats['avg_time']
                best_api = api_name
        
        return best_api
    
    def get_stats_summary(self) -> Dict[str, Dict]:
        """获取性能统计摘要"""
        return self.stats.copy()

api_performance = APIPerformance()

class PriceMonitor:
    def __init__(self):
        self.subscriptions: Dict[str, Set[str]] = {}  # socket_id -> stock_codes
        self.price_cache: Dict[str, tuple[float, datetime, str]] = {}  # (价格, 时间戳, 来源)
        self.running = False
        self.task: asyncio.Task | None = None
        self.CACHE_TTL = 0.5  # 0.5秒缓存（毫秒级实时性）
        self.update_interval = 0.5  # 0.5秒更新一次价格（500ms）
    
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
    
    async def fetch_stock_info_sina(self, stock_code: str) -> tuple[Optional[float], Optional[str], str]:
        """使用新浪财经API获取A股价格和名称（免费）
        返回: (价格, 名称, 来源)"""
        start_time = time.time()
        try:
            normalized_code = self._normalize_stock_code(stock_code)
            url = f"http://hq.sinajs.cn/list={normalized_code}"
            
            # 使用HTTP连接器，避免SSL问题
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=2)) as resp:  # 减少超时到2秒
                    if resp.status == 200:
                        text = await resp.text()
                        # 新浪API返回格式：var hq_str_sh600879="航天电子,15.50,15.60,15.55,15.56,..."
                        # 数据格式：股票名称,今日开盘价,昨日收盘价,当前价格,今日最高价,今日最低价,...
                        if text and '=' in text:
                            data_str = text.split('=')[1].strip().strip('"')
                            if data_str and ',' in data_str:
                                parts = data_str.split(',')
                                if len(parts) >= 4:
                                    # parts[0] 是股票名称
                                    # parts[3] 是当前价格（实时价格）
                                    stock_name = parts[0].strip()
                                    try:
                                        price = float(parts[3])
                                        if price > 0:  # 确保价格有效
                                            response_time = time.time() - start_time
                                            api_performance.record("新浪财经", response_time, True)
                                            logger.debug(f"新浪API返回 {stock_code}: 名称={stock_name}, 价格={price}, 延迟={response_time*1000:.1f}ms")
                                            return (round(price, 2), stock_name, "新浪财经")
                                        else:
                                            logger.warning(f"新浪API返回 {stock_code} 价格无效: {price}")
                                    except (ValueError, IndexError) as e:
                                        logger.error(f"解析新浪API价格失败 {stock_code}: {e}, parts={parts[:10]}")
            response_time = time.time() - start_time
            api_performance.record("新浪财经", response_time, False)
            return (None, None, "新浪财经")
        except Exception as e:
            response_time = time.time() - start_time
            api_performance.record("新浪财经", response_time, False)
            logger.error(f"从新浪API获取股票 {stock_code} 信息失败: {e}")
            return (None, None, "新浪财经")
    
    async def fetch_stock_price_sina(self, stock_code: str) -> tuple[Optional[float], str]:
        """使用新浪财经API获取A股价格（免费）
        返回: (价格, 来源)"""
        price, _, source = await self.fetch_stock_info_sina(stock_code)
        return (price, source)
    
    async def fetch_stock_info_tencent(self, stock_code: str) -> tuple[Optional[float], Optional[str], str]:
        """使用腾讯财经API获取A股价格和名称（备用方案）
        返回: (价格, 名称, 来源)"""
        start_time = time.time()
        try:
            normalized_code = self._normalize_stock_code(stock_code)
            # 腾讯API格式：使用HTTP避免SSL证书问题
            url = f"http://qt.gtimg.cn/q={normalized_code}"
            
            # 使用HTTP连接器，避免SSL问题
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=2)) as resp:  # 减少超时到2秒
                    if resp.status == 200:
                        text = await resp.text()
                        # 腾讯API返回格式：v_sh600879="航天电子~15.50~15.60~..."
                        if text and '=' in text:
                            data_str = text.split('=')[1].strip().strip('"')
                            if data_str and '~' in data_str:
                                parts = data_str.split('~')
                                if len(parts) >= 4:
                                    # parts[1] 是股票名称
                                    # parts[3] 是当前价格
                                    stock_name = parts[1].strip()
                                    price = float(parts[3])
                                    response_time = time.time() - start_time
                                    api_performance.record("腾讯财经", response_time, True)
                                    logger.debug(f"腾讯API返回 {stock_code}: 名称={stock_name}, 价格={price}, 延迟={response_time*1000:.1f}ms")
                                    return (round(price, 2), stock_name, "腾讯财经")
            response_time = time.time() - start_time
            api_performance.record("腾讯财经", response_time, False)
            return (None, None, "腾讯财经")
        except Exception as e:
            response_time = time.time() - start_time
            api_performance.record("腾讯财经", response_time, False)
            logger.error(f"从腾讯API获取股票 {stock_code} 信息失败: {e}")
            return (None, None, "腾讯财经")
    
    async def fetch_stock_price_tencent(self, stock_code: str) -> tuple[Optional[float], str]:
        """使用腾讯财经API获取A股价格（备用方案）
        返回: (价格, 来源)"""
        price, _, source = await self.fetch_stock_info_tencent(stock_code)
        return (price, source)
    
    async def fetch_stock_name(self, stock_code: str) -> Optional[str]:
        """获取股票名称
        返回: 股票名称，如果失败返回None"""
        try:
            # 尝试从新浪API获取
            _, name, _ = await self.fetch_stock_info_sina(stock_code)
            if name:
                return name
            
            # 如果失败，尝试腾讯API
            _, name, _ = await self.fetch_stock_info_tencent(stock_code)
            if name:
                return name
            
            return None
        except Exception as e:
            logger.error(f"获取股票 {stock_code} 名称失败: {e}")
            return None
    
    async def fetch_stock_price(self, stock_code: str, force_refresh: bool = False) -> tuple[float, str]:
        """获取股票价格（带缓存和重试机制）
        返回: (价格, 来源)
        force_refresh: 是否强制刷新，忽略缓存"""
        # 检查缓存（除非强制刷新）
        if not force_refresh:
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
        
        # 检查价格是否变化
        old_price = None
        if stock_code in self.price_cache:
            old_price_data = self.price_cache[stock_code]
            if isinstance(old_price_data, tuple) and len(old_price_data) >= 3:
                old_price = old_price_data[0]
        
        # 更新缓存 (价格, 时间戳, 来源)
        self.price_cache[stock_code] = (price, datetime.utcnow(), source)
        
        # 如果价格变化，触发回调（毫秒级推送）
        if old_price is not None and abs(old_price - price) > 0.001:  # 价格变化超过0.001元
            logger.debug(f"💰 价格变化 {stock_code}: {old_price:.2f} -> {price:.2f}")
            for callback in self.price_change_callbacks:
                try:
                    callback(stock_code, price, source)
                except Exception as e:
                    logger.error(f"价格变化回调执行失败: {e}")
        
        logger.debug(f"获取股票 {stock_code} 价格: {price} (来源: {source})")
        return (price, source)
    
    async def batch_fetch_prices(self, stock_codes: list[str], force_refresh: bool = False) -> Dict[str, Dict[str, any]]:
        """批量获取股票价格
        返回: {stock_code: {"price": float, "source": str}}"""
        prices = {}
        tasks = [self.fetch_stock_price(code, force_refresh=force_refresh) for code in stock_codes]
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
        """价格更新循环（毫秒级实时更新）"""
        logger.info(f"启动价格监控循环，间隔: {self.update_interval}s")
        while self.running:
            try:
                # 检查交易时间
                if not self.is_trading_time():
                    # 非交易时间，大幅降低频率（例如10秒一次，或者完全停止）
                    # 为了用户体验（可能在非交易时间查看），保持低频更新
                    await asyncio.sleep(5)
                    continue

                # 收集所有需要监控的股票代码
                all_stock_codes = set()
                for stock_codes in self.subscriptions.values():
                    all_stock_codes.update(stock_codes)
                
                if all_stock_codes:
                    # 批量获取价格（强制刷新，忽略缓存，实现毫秒级实时性）
                    prices = await self.batch_fetch_prices(list(all_stock_codes), force_refresh=True)
                    # 仅在有价格变化或特定条件下打日志，避免日志爆炸
                    # logger.debug(f"更新价格: {len(prices)} 只股票")
                
                # 使用设定的间隔
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
