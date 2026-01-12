"""
数据库迁移脚本：为 Trade 表添加 buy_commission 和 sell_commission 字段

运行方式：
cd backend && python3 migrate_add_commission_fields.py
"""

import asyncio
from sqlalchemy import text
from app.database import engine

async def migrate():
    """执行迁移"""
    async with engine.begin() as conn:
        print("🔄 开始迁移：添加 buy_commission 和 sell_commission 字段...")
        
        # 检查字段是否已存在（SQLite使用PRAGMA）
        result = await conn.execute(text("PRAGMA table_info(trades)"))
        columns = [row[1] for row in result.fetchall()]
        exists = 'buy_commission' in columns
        
        if exists:
            print("⚠️  字段 buy_commission 已存在，跳过迁移")
            return
        
        # 添加 buy_commission 字段
        await conn.execute(text("""
            ALTER TABLE trades 
            ADD COLUMN buy_commission FLOAT DEFAULT 0
        """))
        print("✅ 已添加 buy_commission 字段")
        
        # 添加 sell_commission 字段
        await conn.execute(text("""
            ALTER TABLE trades 
            ADD COLUMN sell_commission FLOAT DEFAULT 0
        """))
        print("✅ 已添加 sell_commission 字段")
        
        # 将现有的 commission 值拆分到 buy_commission（对于开仓）
        # 对于已平仓的交易，假设买卖手续费各占一半
        await conn.execute(text("""
            UPDATE trades 
            SET buy_commission = CASE 
                WHEN status = 'open' THEN commission
                ELSE commission / 2
            END,
            sell_commission = CASE 
                WHEN status = 'closed' THEN commission / 2
                ELSE 0
            END
            WHERE commission > 0
        """))
        print("✅ 已迁移现有数据")
        
        print("🎉 迁移完成！")

if __name__ == "__main__":
    asyncio.run(migrate())
