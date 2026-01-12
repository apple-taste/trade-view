"""
数据库迁移脚本：添加 profit_loss 字段
运行此脚本为现有的 trades 表添加 profit_loss 字段
"""
import asyncio
import aiosqlite

async def migrate():
    db_path = "./database.db"
    
    async with aiosqlite.connect(db_path) as db:
        # 检查 profit_loss 列是否存在
        cursor = await db.execute("PRAGMA table_info(trades)")
        columns = [row[1] for row in await cursor.fetchall()]
        
        if 'profit_loss' not in columns:
            print("📝 添加 profit_loss 字段...")
            await db.execute("ALTER TABLE trades ADD COLUMN profit_loss FLOAT")
            await db.commit()
            print("✅ 数据库迁移完成：profit_loss 字段已添加")
        else:
            print("✅ profit_loss 字段已存在，无需迁移")
        
        # 验证
        cursor = await db.execute("PRAGMA table_info(trades)")
        columns = [row[1] for row in await cursor.fetchall()]
        print(f"📊 trades 表的列: {', '.join(columns)}")

if __name__ == "__main__":
    asyncio.run(migrate())
