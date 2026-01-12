"""
数据库迁移脚本：为 User 表添加 email_alerts_enabled 字段

运行方式：
cd backend && python3 migrate_add_email_alerts.py
"""

import asyncio
from sqlalchemy import text
from app.database import engine

async def migrate():
    """执行迁移"""
    async with engine.begin() as conn:
        print("🔄 开始迁移：添加 email_alerts_enabled 字段...")
        
        # 检查字段是否已存在（SQLite使用PRAGMA）
        result = await conn.execute(text("PRAGMA table_info(users)"))
        columns = [row[1] for row in result.fetchall()]
        exists = 'email_alerts_enabled' in columns
        
        if exists:
            print("⚠️  字段已存在，跳过迁移")
            return
        
        # 添加 email_alerts_enabled 字段
        await conn.execute(text("""
            ALTER TABLE users 
            ADD COLUMN email_alerts_enabled BOOLEAN DEFAULT 0
        """))
        print("✅ 已添加 email_alerts_enabled 字段")
        
        print("🎉 迁移完成！")

if __name__ == "__main__":
    asyncio.run(migrate())
