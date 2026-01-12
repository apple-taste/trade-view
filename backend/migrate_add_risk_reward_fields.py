"""
数据库迁移脚本：为 Trade 表添加理论和实际风险回报比字段

运行方式：
cd backend && python3 migrate_add_risk_reward_fields.py
"""

import asyncio
from sqlalchemy import text
from app.database import engine

async def migrate():
    """执行迁移"""
    async with engine.begin() as conn:
        print("🔄 开始迁移：添加 theoretical_risk_reward_ratio 和 actual_risk_reward_ratio 字段...")
        
        # 检查字段是否已存在（SQLite使用PRAGMA）
        result = await conn.execute(text("PRAGMA table_info(trades)"))
        columns = [row[1] for row in result.fetchall()]
        exists = 'theoretical_risk_reward_ratio' in columns
        
        if exists:
            print("⚠️  字段已存在，跳过迁移")
            return
        
        # 添加 theoretical_risk_reward_ratio 字段
        await conn.execute(text("""
            ALTER TABLE trades 
            ADD COLUMN theoretical_risk_reward_ratio FLOAT
        """))
        print("✅ 已添加 theoretical_risk_reward_ratio 字段")
        
        # 添加 actual_risk_reward_ratio 字段
        await conn.execute(text("""
            ALTER TABLE trades 
            ADD COLUMN actual_risk_reward_ratio FLOAT
        """))
        print("✅ 已添加 actual_risk_reward_ratio 字段")
        
        print("🎉 迁移完成！")

if __name__ == "__main__":
    asyncio.run(migrate())
