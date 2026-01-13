from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.middleware.auth import get_current_user
from app.database import User
from app.services.price_monitor import price_monitor

router = APIRouter()

class PriceResponse(BaseModel):
    stock_code: str
    price: float
    source: Optional[str] = None
    timestamp: str

@router.get(
    "/{stock_code}",
    response_model=PriceResponse,
    summary="获取单个股票价格",
    description="获取指定股票代码的实时价格，包含价格来源信息"
)
async def get_stock_price(
    stock_code: str,
    force_refresh: bool = False,  # 强制刷新参数
    current_user: User = Depends(get_current_user)
):
    """获取单个股票价格
    force_refresh: 是否强制刷新，忽略缓存"""
    price, source = await price_monitor.fetch_stock_price(stock_code, force_refresh=force_refresh)
    if price == 0.0:
        raise HTTPException(status_code=404, detail=f"无法获取股票 {stock_code} 的价格")
    
    from datetime import datetime
    return PriceResponse(
        stock_code=stock_code,
        price=price,
        source=source,
        timestamp=datetime.utcnow().isoformat()
    )

class BatchPriceResponse(BaseModel):
    stock_code: str
    price: float
    source: str
    timestamp: str

@router.post(
    "/batch",
    response_model=List[BatchPriceResponse],
    summary="批量获取股票价格",
    description="批量获取多个股票代码的价格，包含价格来源信息"
)
async def get_batch_prices(
    stock_codes: List[str],
    force_refresh: bool = False,  # 强制刷新参数
    current_user: User = Depends(get_current_user)
):
    """批量获取股票价格
    force_refresh: 是否强制刷新，忽略缓存"""
    prices = await price_monitor.batch_fetch_prices(stock_codes, force_refresh=force_refresh)
    
    from datetime import datetime
    return [
        BatchPriceResponse(
            stock_code=code,
            price=price_info.get("price", 0.0),
            source=price_info.get("source", "未知"),
            timestamp=datetime.utcnow().isoformat()
        )
        for code, price_info in prices.items()
    ]

@router.get(
    "/performance",
    summary="获取API性能统计",
    description="获取各API的性能统计信息，包括平均响应时间、成功率等"
)
async def get_api_performance(
    current_user: User = Depends(get_current_user)
):
    """获取API性能统计"""
    stats = api_performance.get_stats_summary()
    
    # 格式化统计数据
    formatted_stats = {}
    for api_name, data in stats.items():
        formatted_stats[api_name] = {
            "调用次数": data['count'],
            "成功次数": data['success_count'],
            "失败次数": data['fail_count'],
            "成功率": f"{(data['success_count'] / data['count'] * 100):.1f}%" if data['count'] > 0 else "0%",
            "平均延迟": f"{data['avg_time']*1000:.1f}ms",
            "最小延迟": f"{data['min_time']*1000:.1f}ms" if data['min_time'] != float('inf') else "N/A",
            "最大延迟": f"{data['max_time']*1000:.1f}ms"
        }
    
    best_api = api_performance.get_best_api()
    
    return {
        "statistics": formatted_stats,
        "best_api": best_api,
        "recommendation": f"当前推荐使用: {best_api}" if best_api else "暂无统计数据"
    }
