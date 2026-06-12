from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import re

from database.db import get_db
from keyboards.main_menu import main_menu

router = Router()


class SettingsState(StatesGroup):
    waiting_time = State()


def normalize_time(time_str: str) -> str | None:
    """Проверяет ЧЧ:ММ и нормализует к ближайшему часу (рассылка идёт раз в час).
    ФИКС: раньше принималось даже 99:99."""
    m = re.match(r"^(\d{1,2}):(\d{2})$", time_str.strip())
    if not m:
        return None
    hh, mm = int(m.group(1)), int(m.group(2))
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        return None
    if mm >= 30:
        hh = (hh + 1) % 24
    return f"{hh:02d}:00"


def settings_keyboard(lang: str, hourly: bool) -> InlineKeyboardMarkup:
    if lang == "uz":
        hourly_text = "🔔 Eslatmalar: YOQILGAN" if hourly else "🔕 Eslatmalar: OCHIQ EMAS"
        lang_text = "🌐 Til / Язык"
        time_text = "⏰ Dars vaqti"
        stats_text = "📊 Mening statistikam"
        reset_text = "🔄 Darsni qayta boshlash"
    else:
        hourly_text = "🔔 Напоминания: ВКЛ" if hourly else "🔕 Напоминания: ВЫКЛ"
        lang_text = "🌐 Язык / Til"
        time_text = "⏰ Время урока"
        stats_text = "📊 Моя статистика"
        reset_text = "🔄 Сбросить прогресс урока"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=lang_text,    callback_data="set:language")],
        [InlineKeyboardButton(text=time_text,    callback_data="set:time")],
        [InlineKeyboardButton(text=hourly_text,  callback_data="set:toggle_reminders")],
        [InlineKeyboardButton(text=stats_text,   callback_data="set:stats")],
        [InlineKeyboardButton(text=reset_text,   callback_data="set:reset_lesson")],
    ])


async def get_hourly(user_id: int) -> bool:
    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT hourly_enabled FROM reminders WHERE user_id=?", (user_id,)
    )
    await db.close()
    return bool(rows[0]["hourly_enabled"]) if rows else True


async def get_morning_time(user: dict) -> str:
    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT morning_time FROM reminders WHERE user_id=?", (user["id"],)
    )
    await db.close()
    return rows[0]["morning_time"] if rows else user["notify_time"]


def build_settings_text(lang: str, morning: str, hourly: bool) -> str:
    if lang == "uz":
        hourly_label = "Yoqilgan" if hourly else "Ochiq emas"
        return (
            "<b>Sozlamalar</b>\n\n"
            "Til: O'zbekcha\n"
            "Dars vaqti: " + morning + "\n"
            "Eslatmalar: " + hourly_label + "\n\n"
            "Quyidagi tugmalardan birini tanlang:"
        )
    else:
        hourly_label = "Включены" if hourly else "Выключены"
        return (
            "<b>Настройки</b>\n\n"
            "Язык: Русский\n"
            "Время урока: " + morning + "\n"
            "Напоминания: " + hourly_label + "\n\n"
            "Выбери что хочешь изменить:"
        )


@router.message(F.text.in_(["Настройки", "Sozlamalar", "⚙️ Настройки", "⚙️ Sozlamalar"]))
async def show_settings(message: Message, db_user: dict):
    if not db_user:
        await message.answer("Сначала нажми /start")
        return
    lang = db_user["language"]
    hourly = await get_hourly(db_user["id"])
    morning = await get_morning_time(db_user)
    text = build_settings_text(lang, morning, hourly)
    await message.answer(text, parse_mode="HTML", reply_markup=settings_keyboard(lang, hourly))


@router.callback_query(F.data == "set:language")
async def change_language(call: CallbackQuery, db_user: dict):
    lang = db_user["language"]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Русский",   callback_data="setlang:ru"),
            InlineKeyboardButton(text="O'zbekcha", callback_data="setlang:uz"),
        ],
        [InlineKeyboardButton(text="Назад / Orqaga", callback_data="set:back")],
    ])
    text = "Tilni tanlang:" if lang == "uz" else "Выбери язык:"
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()


@router.callback_query(F.data.startswith("setlang:"))
async def set_language(call: CallbackQuery, db_user: dict):
    new_lang = call.data.split(":")[1]
    db = await get_db()
    await db.execute(
        "UPDATE users SET language=? WHERE telegram_id=?",
        (new_lang, call.from_user.id)
    )
    await db.commit()
    await db.close()
    msg = "Til o'zgartirildi!" if new_lang == "uz" else "Язык изменён!"
    await call.message.edit_text(msg)
    await call.message.answer("OK", reply_markup=main_menu(new_lang))
    await call.answer()


@router.callback_query(F.data == "set:time")
async def change_time(call: CallbackQuery, state: FSMContext, db_user: dict):
    lang = db_user["language"]
    times = ["06:00", "07:00", "08:00", "09:00", "10:00", "11:00"]
    buttons = [InlineKeyboardButton(text=t, callback_data="settime:" + t) for t in times]
    custom = "O'z vaqtim" if lang == "uz" else "Своё время"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        buttons[:3],
        buttons[3:],
        [InlineKeyboardButton(text=custom,           callback_data="settime:custom")],
        [InlineKeyboardButton(text="Назад / Orqaga", callback_data="set:back")],
    ])
    text = "Yangi vaqtni tanlang:" if lang == "uz" else "Выбери новое время урока:"
    await call.message.edit_text(text, reply_markup=kb)
    await state.set_state(SettingsState.waiting_time)
    await call.answer()


@router.callback_query(SettingsState.waiting_time, F.data.startswith("settime:"))
async def set_time_button(call: CallbackQuery, state: FSMContext, db_user: dict):
    # ФИКС: callback "settime:07:00" резался обычным split(":")[1] до "07",
    # и в базу сохранялось "07" вместо "07:00" — урок не отправлялся никогда.
    value = call.data.split(":", 1)[1]
    lang = db_user["language"]
    if value == "custom":
        prompt = "Vaqtni yozing (07:00):" if lang == "uz" else "Напиши время (07:00):"
        await call.message.edit_text(prompt)
        await call.answer()
        return
    await _save_time(call.message, state, db_user, value, lang)
    await call.answer()


@router.message(SettingsState.waiting_time)
async def set_time_manual(message: Message, state: FSMContext, db_user: dict):
    lang = db_user["language"]
    time_str = normalize_time(message.text or "")
    if not time_str:
        err = "Noto'g'ri format. 07:00 kabi yozing" if lang == "uz" else "Неверный формат. Напиши как 07:00"
        await message.answer(err)
        return
    await _save_time(message, state, db_user, time_str, lang)


async def _save_time(target, state, db_user, time_str, lang):
    db = await get_db()
    await db.execute("UPDATE users SET notify_time=? WHERE id=?", (time_str, db_user["id"]))
    await db.execute("UPDATE reminders SET morning_time=? WHERE user_id=?", (time_str, db_user["id"]))
    await db.commit()
    await db.close()
    await state.clear()
    msg = "Vaqt o'zgartirildi! Endi dars " + time_str + " da keladi." if lang == "uz" \
          else "Время изменено! Теперь урок приходит в " + time_str + "."
    await target.answer(msg, reply_markup=main_menu(lang))


@router.callback_query(F.data == "set:toggle_reminders")
async def toggle_reminders(call: CallbackQuery, db_user: dict):
    lang = db_user["language"]
    hourly = await get_hourly(db_user["id"])
    new_val = not hourly
    db = await get_db()
    await db.execute("UPDATE reminders SET hourly_enabled=? WHERE user_id=?", (new_val, db_user["id"]))
    await db.commit()
    await db.close()
    msg = "Eslatmalar yoqildi!" if new_val else "Eslatmalar o'chirildi!"
    if lang == "ru":
        msg = "Напоминания включены!" if new_val else "Напоминания выключены!"
    morning = await get_morning_time(db_user)
    text = build_settings_text(lang, morning, new_val)
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=settings_keyboard(lang, new_val))
    await call.answer(msg, show_alert=True)


@router.callback_query(F.data == "set:reset_lesson")
async def reset_lesson_confirm(call: CallbackQuery, db_user: dict):
    lang = db_user["language"]
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Ha / Да",  callback_data="set:reset_confirm"),
        InlineKeyboardButton(text="Yo'q / Нет", callback_data="set:back"),
    ]])
    text = "Darsni qayta boshlaysizmi?" if lang == "uz" else "Сбросить прогресс текущего урока?"
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()


@router.callback_query(F.data == "set:reset_confirm")
async def reset_lesson_do(call: CallbackQuery, db_user: dict):
    lang = db_user["language"]
    db = await get_db()
    lesson_num = db_user["current_lesson"]
    if lesson_num > 1:
        await db.execute("UPDATE users SET current_lesson=current_lesson-1 WHERE id=?", (db_user["id"],))
    await db.execute("DELETE FROM progress WHERE user_id=? AND lesson_id=?", (db_user["id"], lesson_num))
    await db.commit()
    await db.close()
    msg = "Dars qayta boshlandi!" if lang == "uz" else "Урок сброшен! Нажми Урок дня."
    await call.message.edit_text(msg)
    await call.answer()


@router.callback_query(F.data == "set:stats")
async def settings_stats(call: CallbackQuery, db_user: dict):
    from services.statistics_service import format_stats_message
    lang = db_user["language"]
    text = await format_stats_message(db_user["id"], lang)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Назад / Orqaga", callback_data="set:back")
    ]])
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await call.answer()


@router.callback_query(F.data == "set:back")
async def settings_back(call: CallbackQuery, db_user: dict):
    lang = db_user["language"]
    hourly = await get_hourly(db_user["id"])
    morning = await get_morning_time(db_user)
    text = build_settings_text(lang, morning, hourly)
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=settings_keyboard(lang, hourly))
    await call.answer()
