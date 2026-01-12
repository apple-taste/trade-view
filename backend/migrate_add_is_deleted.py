"""
数据库迁移脚本：添加 is_deleted 字段
运行此脚本为现有的 trades 表添加 is_deleted 字段
"""
import asyncio
import aiosqlite

async def migrate():
    db_path = "./database.db"
    
    async with aiosqlite.connect(db_path) as db:
        # 检查 is_deleted 列是否存在
        cursor = await db.execute("PRAGMA table_info(trades)")
        columns = [row[1] for row in await cursor.fetchall()]
        
        if 'is_deleted' not in columns:
            print("📝 添加 is_deleted 字段...")
            await db.execute("ALTER TABLE trades ADD COLUMN is_deleted BOOLEAN DEFAULT 0")
            await db.execute("CREATE INDEX IF NOT EXISTS ix_trades_is_deleted ON trades(is_deleted)")
            await db.commit()
            print("✅ 数据库迁移完成：is_deleted 字段已添加")
        else:
            print("✅ is_deleted 字段已存在，无需迁移")
        
        # 验证
        cursor = await db.execute("PRAGMA table_info(trades)")
        columns = [row[1] for row in await cursor.fetchall()]
        print(f"📊 trades 表的列: {', '.join(columns)}")

if __name__ == "__main__":
    asyncio.run(migrate())
