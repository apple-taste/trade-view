#!/usr/bin/env python3
"""
数据库迁移脚本：为 users 表添加 initial_capital / initial_capital_date

目的：
- “清空全部交易”或“删除最后一笔交易”后，总资产必须恢复到初始入金
- 资金曲线重算必须有稳定锚点（避免 CapitalHistory 被覆盖导致初始值丢失）

回填策略：
- 优先使用该用户最早的 capital_history 记录作为初始入金与日期
- 若用户没有 capital_history，则使用默认 100000 与今天日期
"""

import sqlite3
from datetime import date


def migrate() -> None:
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA table_info(users)")
        cols = [c[1] for c in cursor.fetchall()]

        if "initial_capital" not in cols:
            cursor.execute("ALTER TABLE users ADD COLUMN initial_capital REAL")
            print("✅ users.initial_capital added")
        else:
            print("ℹ️ users.initial_capital already exists")

        if "initial_capital_date" not in cols:
            cursor.execute("ALTER TABLE users ADD COLUMN initial_capital_date DATE")
            print("✅ users.initial_capital_date added")
        else:
            print("ℹ️ users.initial_capital_date already exists")

        # 回填：用最早 capital_history 作为初始锚点
        cursor.execute("SELECT id FROM users")
        user_ids = [r[0] for r in cursor.fetchall()]

        for uid in user_ids:
            cursor.execute(
                """
                SELECT date, capital
                FROM capital_history
                WHERE user_id = ?
                ORDER BY date ASC
                LIMIT 1
                """,
                (uid,),
            )
            row = cursor.fetchone()
            if row:
                init_date, init_capital = row[0], row[1]
            else:
                init_date, init_capital = str(date.today()), 100000.0

            cursor.execute(
                """
                UPDATE users
                SET initial_capital = COALESCE(initial_capital, ?),
                    initial_capital_date = COALESCE(initial_capital_date, ?)
                WHERE id = ?
                """,
                (init_capital, init_date, uid),
            )

        conn.commit()
        print("✅ backfill complete")

    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()

