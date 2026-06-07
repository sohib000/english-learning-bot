from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
import os, re

from states.registration import Registration
from utils.helpers import clean_name
from database.repository.users import create_user, get_user, update_language
from keyboards.main_menu import main_menu

router = Router()

WELCOME_IMAGE = "assets/welcome.jpg"

WELCOME_TEXT = {
    "ru": (
        "👋 Привет, <b>{name}</b>!\n\n"
        "📚 <b>English Daily</b> — твой ежедневный тренер английского.\n\n"
        "🎯 Что тебя ждёт:\n"
        "• Новый урок каждое утро\n"
        "• Аудио произношение носителя\n"
        "• Вечерний тест для закрепления\n"
        "• Напоминания в течение дня\n\n"
        "📈 Цель: <b>1000 слов</b> — шаг за шагом!\n\n"
        "Выбери язык интерфейса 👇"
    ),
    "uz": (
        "👋 Salom, <b>{name}</b>!\n\n"
        "📚 <b>English Daily</b> — kunlik ingliz tili treneringiz.\n\n"
        "🎯 Seni nima kutmoqda:\n"
        "• Har ertalab yangi dars\n"
        "• Ona tili so'zlovchisidan audio talaffuz\n"
        "• Mustahkamlash uchun kechki test\n"
        "• Kun davomida eslatmalar\n\n"
        "📈 Maqsad: <b>1000 so'z</b> — qadam ba qadam!\n\n"
        "Interfeys tilini tanlang 👇"
    ),
}

LANG_KEYBOARD = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="🇷🇺 Русский",   callback_data="lang:ru"),
        InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang:uz"),
    ]
])

TIME_TEXT = {
    "ru": (
        "⏰ <b>Когда присылать утренний урок?</b>\n\n"
        "Выбери удобное время или напиши своё в формате <code>ЧЧ:ММ</code>"
    ),
    "uz": (
        "⏰ <b>Ertalabki darsni qachon yuborish kerak?</b>\n\n"
        "Qulay vaqtni tanlang yoki <code>HH:MM</code> formatida yozing"
    ),
}

def time_keyboard(lang: str) -> InlineKeyboardMarkup:
    times = ["06:00", "07:00", "08:00", "09:00", "10:00"]
    buttons = [InlineKeyboardButton(text=t, callback_data=f"time:{t}") for t in times]
    custom_text = "✏️ Своё время" if lang == "ru" else "✏️ O'z vaqtim"
    return InlineKeyboardMarkup(inline_keyboard=[
        buttons[:3],
        buttons[3:],
        [InlineKeyboardButton(text=custom_text, callback_data="time:custom")],
    ])

def ready_text(lang: str, notify_time: str) -> str:
    if lang == "ru":
        return (
            f"✅ <b>Всё готово!</b>\n\n"
            f"🌅 Первый урок придёт в <b>{notify_time}</b>\n\n"
            f"А пока — загляни в урок дня прямо сейчас!\n"
            f"Нажми кнопку <b>📖 Урок дня</b> внизу 👇"
        )
    return (
        f"✅ <b>Hammasi tayyor!</b>\n\n"
        f"🌅 Birinchi dars <b>{notify_time}</b> da keladi\n\n"
        f"Hoziroq bugungi darsga qarang!\n"
        f"Pastdagi <b>📖 Bugungi dars</b> tugmasini bosing 👇"
    )


# ══════════════════════════════════════════
#  /start
# ══════════════════════════════════════════
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)

    if user:
        lang = user["language"]
        greeting = "С возвращением! 👋" if lang == "ru" else "Qaytib keldingiz! 👋"
        await message.answer(greeting, reply_markup=main_menu(lang))
        return

    name = clean_name(message.from_user.first_name or "")
    caption = WELCOME_TEXT["ru"].format(name=name)

    if os.path.exists(WELCOME_IMAGE):
        photo = FSInputFile(WELCOME_IMAGE)
        await message.answer_photo(
            photo=photo,
            caption=caption,
            parse_mode="HTML",
            reply_markup=LANG_KEYBOARD,
        )
    else:
        await message.answer(caption, parse_mode="HTML", reply_markup=LANG_KEYBOARD)

    await state.set_state(Registration.choosing_language)


# ══════════════════════════════════════════
#  Выбор языка — новый пользователь
# ══════════════════════════════════════════
@router.callback_query(Registration.choosing_language, F.data.startswith("lang:"))
async def choose_language(call: CallbackQuery, state: FSMContext):
    lang = call.data.split(":")[1]
    await state.update_data(language=lang)

    await call.message.answer(
        TIME_TEXT[lang],
        parse_mode="HTML",
        reply_markup=time_keyboard(lang),
    )
    await state.set_state(Registration.choosing_time)
    await call.answer()


# ══════════════════════════════════════════
#  Выбор времени — кнопка
# ══════════════════════════════════════════
@router.callback_query(Registration.choosing_time, F.data.startswith("time:"))
async def choose_time_button(call: CallbackQuery, state: FSMContext):
    value = call.data.split(":")[1]
    data = await state.get_data()
    lang = data["language"]

    if value == "custom":
        prompt = "✏️ Напиши время в формате <code>07:00</code>" if lang == "ru" \
                 else "✏️ Vaqtni <code>07:00</code> formatida yozing"
        await call.message.answer(prompt, parse_mode="HTML")
        await call.answer()
        return

    await _finish_registration(call.message, state, lang, value, call.from_user.first_name)
    await call.answer()


# ══════════════════════════════════════════
#  Выбор времени — ввод вручную
# ══════════════════════════════════════════
@router.message(Registration.choosing_time)
async def choose_time_manual(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data["language"]
    time_str = message.text.strip()

    if not re.match(r"^\d{2}:\d{2}$", time_str):
        err = "❌ Неверный формат. Напиши как <code>07:00</code>" if lang == "ru" \
              else "❌ Noto'g'ri format. <code>07:00</code> kabi yozing"
        await message.answer(err, parse_mode="HTML")
        return

    await _finish_registration(message, state, lang, time_str, message.from_user.first_name)


# ══════════════════════════════════════════
#  Завершение регистрации
# ══════════════════════════════════════════
async def _finish_registration(message: Message, state: FSMContext, lang: str, notify_time: str, name: str):
    await create_user(
        telegram_id=message.chat.id,
        name=clean_name(name or ""),
        language=lang,
        notify_time=notify_time,
    )
    await state.clear()
    await message.answer(
        ready_text(lang, notify_time),
        parse_mode="HTML",
        reply_markup=main_menu(lang),
    )


# ══════════════════════════════════════════
#  /language — смена языка для существующих
# ══════════════════════════════════════════
@router.message(F.text.in_(["/language", "/lang"]))
async def change_language_cmd(message: Message, state: FSMContext):
    await message.answer(
        "🌐 Выбери язык / Tilni tanlang:",
        reply_markup=LANG_KEYBOARD,
    )
    await state.set_state(Registration.choosing_language)

@router.callback_query(F.data.startswith("lang:"))
async def switch_language(call: CallbackQuery, state: FSMContext):
    lang = call.data.split(":")[1]
    await update_language(call.from_user.id, lang)
    await state.clear()
    msg = "✅ Язык изменён на Русский" if lang == "ru" else "✅ Til O'zbekchaga o'zgartirildi"
    await call.message.edit_text(msg)
    await call.answer()