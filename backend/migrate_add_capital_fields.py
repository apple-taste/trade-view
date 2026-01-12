#!/usr/bin/env python3
"""
数据库迁移脚本：为 CapitalHistory 表添加 available_funds 和 position_value 字段

同花顺模式：总资产 = 可用资金 + 持仓市值
- available_funds: 可用资金（初始资金 + 已平仓盈亏 - 持仓成本）
- position_value: 持仓市值（所有持仓股票的当前市值）
- capital: 总资产（兼容旧数据，等于 available_funds + position_value）
"""

import asyncio
import sqlite3
from datetime import datetime

def migrate():
    """添加新字段到 capital_history 表"""
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    try:
        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(capital_history)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # 添加 available_funds 字段
        if 'available_funds' not in columns:
            print("添加 available_funds 字段...")
            cursor.execute("""
                ALTER TABLE capital_history 
                ADD COLUMN available_funds REAL
            """)
            # 将现有的 capital 值复制到 available_funds（假设旧数据都是可用资金）
            cursor.execute("""
                UPDATE capital_history 
                SET available_funds = capital
                WHERE available_funds IS NULL
            """)
            print("✅ available_funds 字段添加成功")
        else:
            print("ℹ️  available_funds 字段已存在")
        
        # 添加 position_value 字段
        if 'position_value' not in columns:
            print("添加 position_value 字段...")
            cursor.execute("""
                ALTER TABLE capital_history 
                ADD COLUMN position_value REAL DEFAULT 0.0
            """)
            print("✅ position_value 字段添加成功")
        else:
            print("ℹ️  position_value 字段已存在")
        
        conn.commit()
        print("\n✅ 数据库迁移完成！")
        print("\n📊 同花顺资金模式说明：")
        print("   - capital: 总资产 = available_funds + position_value")
        print("   - available_funds: 可用资金（可用于开新仓）")
        print("   - position_value: 持仓市值（所有持仓股票的当前市值）")
        
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
