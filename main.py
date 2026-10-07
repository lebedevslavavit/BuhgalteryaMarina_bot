"""
Точка входа. Запуск: python main.py
"""
import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from config import BOT_TOKEN, ADMIN_IDS, REPORT_TYPES, PERIODS
from database import (
    init_db, add_company, get_all_companies, delete_company,
    add_task, get_upcoming_tasks, get_overdue_tasks,
    mark_done, delete_task, get_dashboard_stats, get_company_by_id
)
from keyboards import (
    main_menu_kb, tax_system_kb, report_type_kb, period_kb,
    companies_kb, task_actions_kb, company_actions_kb, cancel_kb
)
from scheduler import setup_scheduler, format_date

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


class AddCompany(StatesGroup):
    waiting_unp = State()
    waiting_name = State()
    waiting_tax_system = State()


class AddTask(StatesGroup):
    waiting_company = State()
    waiting_report_type = State()
    waiting_period = State()
    waiting_due_date = State()


async def notify_admins(bot: Bot, text: str):
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text)
        except Exception as e:
            logging.error(f"Не удалось отправить админу {admin_id}: {e}")


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ---------- /start ----------
@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет доступа к этому боту.")
        return
    await state.clear()
    await message.answer(
        "Привет! Я бот-помощник для бухгалтеров.\n\n"
        "Я отслеживаю дедлайны отчетности и налогов, "
        "напоминаю о сроках и веду статистику.\n\n"
        "Выберите действие в меню ниже.",
        reply_markup=main_menu_kb()
    )


# ---------- Дашборд ----------
@dp.message(F.text == "Дашборд")
async def show_dashboard(message: Message, state: FSMContext):
    await state.clear()
    stats = await get_dashboard_stats()
    text = (
        f"Дашборд\n\n"
        f"Компаний: {stats['companies']}\n"
        f"Активных задач: {stats['active_tasks']}\n"
        f"Ближайших (7 дней): {stats['upcoming']}\n"
        f"Просрочено: {stats['overdue']}\n"
        f"Выполнено: {stats['done']}"
    )
    await message.answer(text)


# ---------- Дедлайны на 7 дней ----------
@dp.message(F.text == "Дедлайны (7 дней)")
async def show_upcoming(message: Message, state: FSMContext):
    await state.clear()
    tasks = await get_upcoming_tasks(7)
    if not tasks:
        await message.answer("На ближайшие 7 дней дедлайнов нет.")
        return
    await message.answer("Ближайшие дедлайны:")
    for t in tasks:
        text = (
            f"Компания: {t['company_name']} (УНП: {t['company_unp']})\n"
            f"Отчёт: {t['report_type']}\n"
            f"Период: {t.get('period', '-')}\n"
            f"Срок: {format_date(t['due_date'])}"
        )
        await message.answer(text, reply_markup=task_actions_kb(t["id"]))


# ---------- Просроченные ----------
@dp.message(F.text == "Просроченные")
async def show_overdue(message: Message, state: FSMContext):
    await state.clear()
    tasks = await get_overdue_tasks()
    if not tasks:
        await message.answer("Просроченных дедлайнов нет.")
        return
    await message.answer("Просроченные дедлайны:")
    for t in tasks:
        text = (
            f"Компания: {t['company_name']} (УНП: {t['company_unp']})\n"
            f"Отчёт: {t['report_type']}\n"
            f"Период: {t.get('period', '-')}\n"
            f"Срок: {format_date(t['due_date'])} — просрочено!"
        )
        await message.answer(text, reply_markup=task_actions_kb(t["id"]))


# ---------- Добавить компанию ----------
@dp.message(F.text == "Добавить компанию")
async def start_add_company(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(AddCompany.waiting_unp)
    await message.answer("Введите УНП компании (9 цифр):", reply_markup=cancel_kb())


@dp.message(StateFilter(AddCompany.waiting_unp))
async def process_unp(message: Message, state: FSMContext):
    unp = message.text.strip()
    if not unp.isdigit() or len(unp) != 9:
        await message.answer("УНП должен состоять из 9 цифр. Попробуйте ещё раз:")
        return
    await state.update_data(unp=unp)
    await state.set_state(AddCompany.waiting_name)
    await message.answer("Введите название компании:")


@dp.message(StateFilter(AddCompany.waiting_name))
async def process_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Слишком короткое название. Попробуйте ещё раз:")
        return
    await state.update_data(name=name)
    await state.set_state(AddCompany.waiting_tax_system)
    await message.answer("Выберите систему налогообложения:", reply_markup=tax_system_kb())


@dp.callback_query(StateFilter(AddCompany.waiting_tax_system), F.data.startswith("tax_"))
async def process_tax_system(callback: CallbackQuery, state: FSMContext):
    tax_system = callback.data[4:]
    data = await state.get_data()
    result = await add_company(data["unp"], data["name"], tax_system)

    if result["ok"]:
        await callback.message.answer(
            f"Компания добавлена:\n\n"
            f"Название: {data['name']}\n"
            f"УНП: {data['unp']}\n"
            f"Система: {tax_system}",
            reply_markup=main_menu_kb()
        )
    else:
        await callback.message.answer(
            f"Ошибка: {result['error']}",
            reply_markup=main_menu_kb()
        )

    await state.clear()
    await callback.answer()


# ---------- Добавить дедлайн ----------
@dp.message(F.text == "Добавить дедлайн")
async def start_add_task(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    companies = await get_all_companies()
    if not companies:
        await message.answer("Сначала добавьте хотя бы одну компанию.")
        return
    await state.set_state(AddTask.waiting_company)
    await message.answer("Выберите компанию:", reply_markup=companies_kb(companies))


@dp.callback_query(StateFilter(AddTask.waiting_company), F.data.startswith("company_"))
async def process_task_company(callback: CallbackQuery, state: FSMContext):
    company_id = int(callback.data[8:])
    await state.update_data(company_id=company_id)
    await state.set_state(AddTask.waiting_report_type)
    await callback.message.answer("Выберите тип отчёта:", reply_markup=report_type_kb())
    await callback.answer()


@dp.callback_query(StateFilter(AddTask.waiting_report_type), F.data.startswith("rt_"))
async def process_report_type(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data[3:])
    report_type = REPORT_TYPES[idx]
    await state.update_data(report_type=report_type)
    await state.set_state(AddTask.waiting_period)
    await callback.message.answer("Выберите период:", reply_markup=period_kb())
    await callback.answer()


@dp.callback_query(StateFilter(AddTask.waiting_period), F.data.startswith("period_"))
async def process_period(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data[7:])
    period = PERIODS[idx]
    await state.update_data(period=period)
    await state.set_state(AddTask.waiting_due_date)
    await callback.message.answer("Введите дату дедлайна в формате ДД.ММ.ГГГГ (например, 25.03.2026):")
    await callback.answer()


@dp.message(StateFilter(AddTask.waiting_due_date))
async def process_due_date(message: Message, state: FSMContext):
    text = message.text.strip()
    try:
        due_date = datetime.strptime(text, "%d.%m.%Y").date().isoformat()
    except ValueError:
        await message.answer("Неверный формат. Введите дату как ДД.ММ.ГГГГ:")
        return

    data = await state.get_data()
    await add_task(data["company_id"], data["report_type"], data["period"], due_date)

    company = await get_company_by_id(data["company_id"])
    company_name = company["name"] if company else "?"
    await message.answer(
        f"Дедлайн добавлен:\n\n"
        f"Компания: {company_name}\n"
        f"Отчёт: {data['report_type']}\n"
        f"Период: {data['period']}\n"
        f"Срок: {text}",
        reply_markup=main_menu_kb()
    )
    await state.clear()


# ---------- Мои компании ----------
@dp.message(F.text == "Мои компании")
async def show_companies(message: Message, state: FSMContext):
    await state.clear()
    companies = await get_all_companies()
    if not companies:
        await message.answer("У вас пока нет добавленных компаний.")
        return
    await message.answer("Ваши компании:", reply_markup=companies_kb(companies))


@dp.callback_query(F.data.startswith("company_"), ~StateFilter(AddTask.waiting_company))
async def show_company_detail(callback: CallbackQuery):
    company_id = int(callback.data[8:])
    company = await get_company_by_id(company_id)
    if not company:
        await callback.answer("Компания не найдена")
        return
    text = (
        f"Компания: {company['name']}\n\n"
        f"УНП: {company['unp']}\n"
        f"Система налогообложения: {company['tax_system']}"
    )
    await callback.message.answer(text, reply_markup=company_actions_kb(company_id))
    await callback.answer()


@dp.callback_query(F.data == "back_companies")
async def back_to_companies(callback: CallbackQuery):
    companies = await get_all_companies()
    await callback.message.answer("Ваши компании:", reply_markup=companies_kb(companies))
    await callback.answer()


@dp.callback_query(F.data.startswith("delcomp_"))
async def delete_company_handler(callback: CallbackQuery):
    company_id = int(callback.data[8:])
    await delete_company(company_id)
    await callback.message.answer("Компания и все её дедлайны удалены.")
    await callback.answer()


# ---------- Действия с задачами ----------
@dp.callback_query(F.data.startswith("done_"))
async def mark_done_handler(callback: CallbackQuery):
    task_id = int(callback.data[5:])
    await mark_done(task_id)
    await callback.message.answer("Отмечено как выполненное.")
    await callback.answer("Готово")


@dp.callback_query(F.data.startswith("del_"))
async def delete_task_handler(callback: CallbackQuery):
    task_id = int(callback.data[4:])
    await delete_task(task_id)
    await callback.message.answer("Дедлайн удалён.")
    await callback.answer("Удалено")


# ---------- Отмена ----------
@dp.message(F.text == "Отмена")
async def cancel_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=main_menu_kb())


# ---------- Запуск ----------
async def main():
    await init_db()
    scheduler = setup_scheduler(bot)
    scheduler.start()
    logging.info("Бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
