"""
Работа с базой данных SQLite (aiosqlite).
"""
import aiosqlite
from datetime import date
from typing import Optional
from config import DB_PATH


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unp TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                tax_system TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                report_type TEXT NOT NULL,
                period TEXT,
                due_date DATE NOT NULL,
                status TEXT DEFAULT 'new',
                reminded_days TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(company_id) REFERENCES companies(id)
            )
        """)
        await db.commit()


async def add_company(unp: str, name: str, tax_system: str) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO companies (unp, name, tax_system) VALUES (?, ?, ?)",
                (unp, name, tax_system)
            )
            await db.commit()
            return {"ok": True}
        except aiosqlite.IntegrityError:
            return {"ok": False, "error": "Компания с таким УНП уже существует"}


async def get_all_companies() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM companies ORDER BY name")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_company_by_id(company_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM companies WHERE id = ?", (company_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def delete_company(company_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM tasks WHERE company_id = ?", (company_id,))
        await db.execute("DELETE FROM companies WHERE id = ?", (company_id,))
        await db.commit()


async def add_task(company_id: int, report_type: str, period: str, due_date: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO tasks (company_id, report_type, period, due_date) VALUES (?, ?, ?, ?)",
            (company_id, report_type, period, due_date)
        )
        await db.commit()


async def get_upcoming_tasks(days: int = 7) -> list[dict]:
    today = date.today()
    end = date.fromordinal(today.toordinal() + days)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT t.id, t.report_type, t.period, t.due_date, t.status,
                   c.name as company_name, c.unp as company_unp, c.tax_system
            FROM tasks t
            JOIN companies c ON t.company_id = c.id
            WHERE t.due_date BETWEEN ? AND ? AND t.status != 'done'
            ORDER BY t.due_date
        """, (today.isoformat(), end.isoformat()))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_overdue_tasks() -> list[dict]:
    today = date.today()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT t.id, t.report_type, t.period, t.due_date, t.status,
                   c.name as company_name, c.unp as company_unp
            FROM tasks t
            JOIN companies c ON t.company_id = c.id
            WHERE t.due_date < ? AND t.status != 'done'
            ORDER BY t.due_date
        """, (today.isoformat(),))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_tasks_for_reminder() -> list[dict]:
    today = date.today()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT t.id, t.report_type, t.period, t.due_date, t.status, t.reminded_days,
                   c.name as company_name, c.unp as company_unp
            FROM tasks t
            JOIN companies c ON t.company_id = c.id
            WHERE t.status != 'done'
            ORDER BY t.due_date
        """)
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def mark_reminded(task_id: int, days_before: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT reminded_days FROM tasks WHERE id = ?", (task_id,))
        row = await cursor.fetchone()
        reminded = row[0] if row and row[0] else ""
        reminded_set = set(reminded.split(",")) if reminded else set()
        reminded_set.add(str(days_before))
        await db.execute(
            "UPDATE tasks SET reminded_days = ? WHERE id = ?",
            (",".join(sorted(reminded_set)), task_id)
        )
        await db.commit()


async def mark_done(task_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tasks SET status = 'done' WHERE id = ?", (task_id,))
        await db.commit()


async def delete_task(task_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        await db.commit()


async def get_dashboard_stats() -> dict:
    today = date.today()
    week_end = date.fromordinal(today.toordinal() + 7)
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM companies")
        companies_count = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM tasks WHERE status = 'new'")
        active_tasks = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT COUNT(*) FROM tasks WHERE due_date BETWEEN ? AND ? AND status != 'done'",
            (today.isoformat(), week_end.isoformat())
        )
        upcoming = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT COUNT(*) FROM tasks WHERE due_date < ? AND status != 'done'",
            (today.isoformat(),)
        )
        overdue = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM tasks WHERE status = 'done'")
        done = (await cursor.fetchone())[0]

    return {
        "companies": companies_count,
        "active_tasks": active_tasks,
        "upcoming": upcoming,
        "overdue": overdue,
        "done": done,
    }
