"""
Конфигурация бота. Все значения берутся из переменных окружения.
"""
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
DB_PATH = os.getenv("DB_PATH", "accountant.db")
REMINDER_DAYS = [int(x) for x in os.getenv("REMINDER_DAYS", "3,1,0").split(",")]

TAX_SYSTEMS = ["ОСН", "УСН", "НПД", "Патент"]

REPORT_TYPES = [
    "НДС",
    "Налог на прибыль",
    "РСВ (страховые взносы)",
    "Налог на доходы физлиц",
    "Налог на имущество",
    "Декларация по УСН",
    "Патент (оплата)",
    "Земельный налог",
    "Экологический налог",
    "Другое",
]

PERIODS = [
    "Январь", "Февраль", "Март", "Q1",
    "Апрель", "Май", "Июнь", "Q2",
    "Июль", "Август", "Сентябрь", "Q3",
    "Октябрь", "Ноябрь", "Декабрь", "Q4",
    "Год",
]
