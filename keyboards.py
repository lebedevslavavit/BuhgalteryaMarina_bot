"""
Клавиатуры (Reply и Inline).
"""
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from config import TAX_SYSTEMS, REPORT_TYPES, PERIODS


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Дашборд")],
            [KeyboardButton(text="Дедлайны (7 дней)"),
             KeyboardButton(text="Просроченные")],
            [KeyboardButton(text="Добавить компанию"),
             KeyboardButton(text="Добавить дедлайн")],
            [KeyboardButton(text="Мои компании")],
        ],
        resize_keyboard=True
    )


def tax_system_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=ts, callback_data=f"tax_{ts}")] for ts in TAX_SYSTEMS
    ])


def report_type_kb() -> InlineKeyboardMarkup:
    kb = []
    row = []
    for i, rt in enumerate(REPORT_TYPES):
        row.append(InlineKeyboardButton(text=rt, callback_data=f"rt_{i}"))
        if len(row) == 2:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    return InlineKeyboardMarkup(inline_keyboard=kb)


def period_kb() -> InlineKeyboardMarkup:
    kb = []
    row = []
    for i, p in enumerate(PERIODS):
        row.append(InlineKeyboardButton(text=p, callback_data=f"period_{i}"))
        if len(row) == 4:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    return InlineKeyboardMarkup(inline_keyboard=kb)


def companies_kb(companies: list[dict]) -> InlineKeyboardMarkup:
    kb = []
    for c in companies:
        kb.append([InlineKeyboardButton(
            text=f"{c['name']} (УНП: {c['unp']})",
            callback_data=f"company_{c['id']}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def task_actions_kb(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Выполнено", callback_data=f"done_{task_id}"),
        InlineKeyboardButton(text="Удалить", callback_data=f"del_{task_id}"),
    ]])


def company_actions_kb(company_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Удалить", callback_data=f"delcomp_{company_id}"),
        InlineKeyboardButton(text="Назад", callback_data="back_companies"),
    ]])


def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отмена")]],
        resize_keyboard=True
    )
