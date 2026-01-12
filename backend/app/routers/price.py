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
    current_user: User = Depends(get_current_user)
):
    """获取单个股票价格"""
    price, source = await price_monitor.fetch_stock_price(stock_code)
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
    current_user: User = Depends(get_current_user)
):
    """批量获取股票价格"""
    prices = await price_monitor.batch_fetch_prices(stock_codes)
    
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
