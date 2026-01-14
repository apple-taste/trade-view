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
    
    async def fetch_stock_info_sina_batch(self, stock_codes: list[str]) -> Dict[str, tuple[float, str, str]]:
        """批量获取新浪财经API股票价格
        返回: {stock_code: (price, name, source)}"""
        if not stock_codes:
            return {}
            
        start_time = time.time()
        try:
            # 标准化所有代码
            normalized_codes = [self._normalize_stock_code(code) for code in stock_codes]
            # 新浪API支持批量，用逗号分隔: list=sh600000,sz000001
            codes_str = ",".join(normalized_codes)
            url = f"http://hq.sinajs.cn/list={codes_str}"
            
            # 映射 normalized_code -> original_code
            code_map = {norm: orig for norm, orig in zip(normalized_codes, stock_codes)}
            
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=3)) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        # 解析结果
                        # 格式: var hq_str_sh600879="...";\nvar hq_str_sz000001="...";
                        results = {}
                        lines = text.split('\n')
                        for line in lines:
                            if 'hq_str_' in line and '=' in line:
                                try:
                                    # 提取代码: var hq_str_sh600879=... -> sh600879
                                    norm_code = line.split('hq_str_')[1].split('=')[0]
                                    if norm_code in code_map:
                                        orig_code = code_map[norm_code]
                                        data_str = line.split('=')[1].strip().strip('";')
                                        if data_str and ',' in data_str:
                                            parts = data_str.split(',')
                                            if len(parts) >= 4:
                                                stock_name = parts[0].strip()
                                                price = float(parts[3])
                                                if price > 0:
                                                    results[orig_code] = (round(price, 2), stock_name, "新浪财经")
                                except Exception as e:
                                    continue
                        
                        response_time = time.time() - start_time
                        api_performance.record("新浪财经(批量)", response_time, True)
                        return results
            
            api_performance.record("新浪财经(批量)", time.time() - start_time, False)
            return {}
        except Exception as e:
            logger.error(f"批量获取新浪API失败: {e}")
            api_performance.record("新浪财经(批量)", time.time() - start_time, False)
            return {}

    async def fetch_stock_info_tencent_batch(self, stock_codes: list[str]) -> Dict[str, tuple[float, str, str]]:
        """批量获取腾讯财经API股票价格
        返回: {stock_code: (price, name, source)}"""
        if not stock_codes:
            return {}
            
        start_time = time.time()
        try:
            # 标准化所有代码
            normalized_codes = [self._normalize_stock_code(code) for code in stock_codes]
            # 腾讯API格式: q=sh600000,sz000001
            codes_str = ",".join(normalized_codes)
            url = f"http://qt.gtimg.cn/q={codes_str}"
            
            # 映射 normalized_code -> original_code
            code_map = {norm: orig for norm, orig in zip(normalized_codes, stock_codes)}
            
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=3)) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        results = {}
                        # 腾讯可能一行返回一个，也可能多行
                        lines = text.split(';')
                        for line in lines:
                            if 'v_' in line and '=' in line:
                                try:
                                    # v_sh600879="...";
                                    norm_code = line.split('v_')[1].split('=')[0]
                                    if norm_code in code_map:
                                        orig_code = code_map[norm_code]
                                        data_str = line.split('=')[1].strip().strip('"')
                                        if data_str and '~' in data_str:
                                            parts = data_str.split('~')
                                            if len(parts) >= 4:
                                                stock_name = parts[1].strip()
                                                price = float(parts[3])
                                                results[orig_code] = (round(price, 2), stock_name, "腾讯财经")
                                except Exception as e:
                                    continue
                        
                        response_time = time.time() - start_time
                        api_performance.record("腾讯财经(批量)", response_time, True)
                        return results
            
            api_performance.record("腾讯财经(批量)", time.time() - start_time, False)
            return {}
        except Exception as e:
            logger.error(f"批量获取腾讯API失败: {e}")
            api_performance.record("腾讯财经(批量)", time.time() - start_time, False)
            return {}

    def is_trading_time(self) -> bool:
        """检查是否在交易时间 (9:10-11:35, 12:55-15:05)"""
        now = datetime.now()
        # 周末不交易
        if now.weekday() >= 5:
            return False
            
        current_time = now.time()
        
        # 上午盘 (含集合竞价)
        morning_start = time.strptime("09:10:00", "%H:%M:%S")
        morning_end = time.strptime("11:35:00", "%H:%M:%S")
        
        # 下午盘
        afternoon_start = time.strptime("12:55:00", "%H:%M:%S")
        afternoon_end = time.strptime("15:05:00", "%H:%M:%S")
        
        # 将当前时间转换为 struct_time 进行比较
        curr = time.strptime(current_time.strftime("%H:%M:%S"), "%H:%M:%S")
        
        return (curr >= morning_start and curr <= morning_end) or \
               (curr >= afternoon_start and curr <= afternoon_end)

    async def fetch_stock_name(self, stock_code: str) -> Optional[str]:
        """获取股票名称
        返回: 股票名称，如果失败返回None"""
        try:
            # 尝试从新浪API获取
            results = await self.fetch_stock_info_sina_batch([stock_code])
            if stock_code in results:
                return results[stock_code][1]
            
            # 如果失败，尝试腾讯API
            results = await self.fetch_stock_info_tencent_batch([stock_code])
            if stock_code in results:
                return results[stock_code][1]
            
            return None
        except Exception as e:
            logger.error(f"获取股票 {stock_code} 名称失败: {e}")
            return None

    async def fetch_stock_price(self, stock_code: str, force_refresh: bool = False) -> tuple[float, str]:
        """获取股票价格（带缓存和重试机制）
        返回: (价格, 来源)
        force_refresh: 是否强制刷新，忽略缓存"""
        # 兼容旧接口
        results = await self.batch_fetch_prices([stock_code], force_refresh=force_refresh)
        if stock_code in results:
            return (results[stock_code]["price"], results[stock_code]["source"])
        return (0.0, "获取失败")

    async def batch_fetch_prices(self, stock_codes: list[str], force_refresh: bool = False) -> Dict[str, Dict[str, any]]:
        """批量获取股票价格 (真正实现批量请求)
        返回: {stock_code: {"price": float, "source": str}}"""
        if not stock_codes:
            return {}
            
        # 分批处理，每批最多30个，避免URL过长
        BATCH_SIZE = 30
        all_results = {}
        
        # 将股票代码分块
        chunks = [stock_codes[i:i + BATCH_SIZE] for i in range(0, len(stock_codes), BATCH_SIZE)]
        
        for chunk in chunks:
            # 1. 尝试新浪批量
            batch_results = await self.fetch_stock_info_sina_batch(chunk)
            
            # 2. 检查哪些失败了，尝试腾讯批量
            failed_codes = [code for code in chunk if code not in batch_results]
            if failed_codes:
                tencent_results = await self.fetch_stock_info_tencent_batch(failed_codes)
                batch_results.update(tencent_results)
            
            # 3. 整理结果，更新缓存
            for code in chunk:
                if code in batch_results:
                    price, _, source = batch_results[code]
                    
                    # 检查价格变化并触发回调
                    old_price = None
                    if code in self.price_cache:
                        old_price_data = self.price_cache[code]
                        if isinstance(old_price_data, tuple) and len(old_price_data) >= 3:
                            old_price = old_price_data[0]
                    
                    # 更新缓存
                    self.price_cache[code] = (price, datetime.utcnow(), source)
                    
                    # 触发回调
                    if hasattr(self, 'price_change_callbacks') and old_price is not None and abs(old_price - price) > 0.001:
                        for callback in self.price_change_callbacks:
                            try:
                                callback(code, price, source)
                            except Exception:
                                pass
                                
                    all_results[code] = {"price": price, "source": source}
                else:
                    # 获取失败，使用缓存
                    cached_data = self.price_cache.get(code, (0.0, datetime.utcnow(), "获取失败"))
                    price = cached_data[0] if isinstance(cached_data, tuple) else 0.0
                    source = cached_data[2] if isinstance(cached_data, tuple) and len(cached_data) >= 3 else "获取失败"
                    # 如果不是获取失败，标记为缓存
                    if source != "获取失败":
                        source += "(缓存)"
                    all_results[code] = {"price": price, "source": source}
                    
        return all_results
    
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
