"""
Планировщик напоминаний (APScheduler).
"""
from datetime import date
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from config import REMINDER_DAYS
from database import get_tasks_for_reminder, mark_reminded


def format_date(due_date_str: str) -> str:
    try:
        d = date.fromisoformat(due_date_str)
        return d.strftime("%d.%m.%Y")
    except Exception:
        return due_date_str


async def send_reminders(bot: Bot):
    today = date.today()
    tasks = await get_tasks_for_reminder()

    for task in tasks:
        try:
            due = date.fromisoformat(task["due_date"])
        except Exception:
            continue

        days_left = (due - today).days

        for days_before in REMINDER_DAYS:
            if days_left == days_before:
                reminded_set = set(task["reminded_days"].split(",")) if task["reminded_days"] else set()
                if str(days_before) in reminded_set:
                    continue

                if days_left > 0:
                    msg = (
                        f"Напоминание (за {days_before} дн.)\n\n"
                        f"Компания: {task['company_name']}\n"
                        f"Отчёт: {task['report_type']}\n"
                        f"Период: {task.get('period', '-')}\n"
                        f"Срок: {format_date(task['due_date'])}\n"
                        f"Осталось дней: {days_left}"
                    )
                elif days_left == 0:
                    msg = (
                        f"Сегодня дедлайн!\n\n"
                        f"Компания: {task['company_name']}\n"
                        f"Отчёт: {task['report_type']}\n"
                        f"Период: {task.get('period', '-')}\n"
                        f"Срок: {format_date(task['due_date'])} — сегодня!"
                    )
                else:
                    msg = (
                        f"Просрочка!\n\n"
                        f"Компания: {task['company_name']}\n"
                        f"Отчёт: {task['report_type']}\n"
                        f"Период: {task.get('period', '-')}\n"
                        f"Срок был: {format_date(task['due_date'])}\n"
                        f"Просрочено на {abs(days_left)} дн."
                    )

                from main import notify_admins
                await notify_admins(bot, msg)
                await mark_reminded(task["id"], days_before)


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="Europe/Minsk")

    scheduler.add_job(
        send_reminders, bot,
        trigger="interval",
        hours=1,
        id="reminder_job",
        replace_existing=True
    )
    return scheduler
