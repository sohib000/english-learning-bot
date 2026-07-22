import os
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from database.db import get_db
from database.repository.lessons import load_lesson
from services.lesson_service import get_lesson_message
from services.audio_service import get_or_generate_audio, get_cached_file_id, save_file_id
from keyboards.lessons import lesson_keyboard

router = Router()

async def get_read_count(user_id: int, lesson_id: int) -> int:
    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT read_count FROM progress WHERE user_id=? AND lesson_id=?",
        (user_id, lesson_id)
    )
    await db.close()
    return (rows[0]["read_count"] or 0) if rows else 0

async def increment_read_count(user_id: int, lesson_id: int) -> int:
    db = await get_db()
    await db.execute("""
        INSERT INTO progress (user_id, lesson_id, read_count)
        VALUES (?, ?, 1)
        ON CONFLICT(user_id, lesson_id)
        DO UPDATE SET read_count = COALESCE(read_count, 0) + 1
    """, (user_id, lesson_id))
    await db.commit()
    rows = await db.execute_fetchall(
        "SELECT read_count FROM progress WHERE user_id=? AND lesson_id=?",
        (user_id, lesson_id)
    )
    await db.close()
    return (rows[0]["read_count"] if rows else 1) or 1

# ══════════════════════════════════════════
#  Показать урок
# ══════════════════════════════════════════
@router.message(F.text.in_(["📖 Урок дня", "📖 Bugungi dars"]))
async def show_lesson(message: Message, db_user: dict):
    if not db_user:
        await message.answer("Сначала нажми /start")
        return
    result = await get_lesson_message(
        level=db_user["current_level"],
        lesson_number=db_user["current_lesson"],
        language=db_user["language"],
    )
    if not result:
        msg = "Barcha darslar tugadi!" if db_user["language"] == "uz" else "Все уроки пройдены!"
        await message.answer(msg)
        return
    lesson_id = result["lesson"]["id"]
    read_count = await get_read_count(db_user["id"], lesson_id)
    await message.answer(
        result["text"], parse_mode="HTML",
        reply_markup=lesson_keyboard(lesson_id, read_count=read_count),
    )

# ══════════════════════════════════════════
#  Кнопка "Я прочитал"
# ══════════════════════════════════════════
@router.callback_query(F.data.startswith("read:"))
async def mark_read(call: CallbackQuery, db_user: dict):
    if not db_user:
        await call.answer("Сначала нажми /start", show_alert=True)
        return
    lesson_id = int(call.data.split(":")[1])
    lang = db_user["language"]
    new_count = await increment_read_count(db_user["id"], lesson_id)

    if lang == "uz":
        if new_count == 1:   toast = "👍 Birinchi marta o'qildi!"
        elif new_count == 2: toast = "💪 Yana bir marta — yaxshi!"
        elif new_count == 3: toast = "🔥 3 marta! So'zlar xotirada!"
        elif new_count == 5: toast = "🏆 5 marta! Siz ajoyibsiz!"
        else:                toast = f"✅ {new_count}-marta o'qildi!"
    else:
        if new_count == 1:   toast = "👍 Первое прочтение!"
        elif new_count == 2: toast = "💪 Ещё раз — отлично!"
        elif new_count == 3: toast = "🔥 3 раза! Слова в памяти!"
        elif new_count == 5: toast = "🏆 5 раз! Молодец!"
        else:                toast = f"✅ Прочитано {new_count} раз!"

    try:
        await call.message.edit_reply_markup(
            reply_markup=lesson_keyboard(lesson_id, read_count=new_count)
        )
    except Exception:
        pass
    await call.answer(toast, show_alert=False)

# ══════════════════════════════════════════
#  Кнопка "Слушать аудио"
#  Теперь сохраняем file_id в БД — аудио не теряется при деплое
# ══════════════════════════════════════════
@router.callback_query(F.data.startswith("audio:"))
async def send_audio(call: CallbackQuery, db_user: dict):
    if not db_user:
        await call.answer("Сначала нажми /start", show_alert=True)
        return

    lang = db_user["language"]
    lesson_id = int(call.data.split(":")[1])
    lesson = load_lesson(db_user["current_level"], lesson_id)

    if not lesson:
        await call.answer()
        return

    caption = "🔊 Diqqat bilan tinglang!" if lang == "uz" else "🔊 Слушай внимательно!"

    # 1. Проверяем file_id в БД (не теряется при деплое)
    file_id = await get_cached_file_id(lesson_id)
    if file_id:
        await call.message.answer_audio(file_id, caption=caption)
        await call.answer()
        return

    # 2. Проверяем локальный кэш
    cached = os.path.join("data/audio/generated", f"lesson_{lesson_id:03d}.mp3")
    if os.path.exists(cached) and os.path.getsize(cached) > 0:
        msg = await call.message.answer_audio(FSInputFile(cached), caption=caption)
        # Сохраняем file_id для будущих запросов
        if msg.audio:
            await save_file_id(lesson_id, msg.audio.file_id)
        await call.answer()
        return

    # 3. Генерируем через gTTS
    await call.answer("⏳ Генерирую аудио...", show_alert=False)
    try:
        new_path = await get_or_generate_audio(lesson["text_en"], lesson["id"])
        if new_path and os.path.exists(new_path) and os.path.getsize(new_path) > 0:
            msg = await call.message.answer_audio(FSInputFile(new_path), caption=caption)
            # Сохраняем file_id
            if msg.audio:
                await save_file_id(lesson_id, msg.audio.file_id)
        else:
            msg = "❌ Audio mavjud emas." if lang == "uz" else "❌ Аудио недоступно."
            await call.message.answer(msg)
    except Exception:
        msg = "❌ Audio xatosi." if lang == "uz" else "❌ Ошибка аудио."
        await call.message.answer(msg)

# ══════════════════════════════════════════
#  Открыть урок из напоминания
# ══════════════════════════════════════════
@router.callback_query(F.data == "open_lesson")
async def open_lesson_from_reminder(call: CallbackQuery, db_user: dict):
    if not db_user:
        await call.answer("Сначала нажми /start", show_alert=True)
        return
    result = await get_lesson_message(
        level=db_user["current_level"],
        lesson_number=db_user["current_lesson"],
        language=db_user["language"],
    )
    if not result:
        await call.answer("Все уроки пройдены!", show_alert=True)
        return
    lesson_id = result["lesson"]["id"]
    read_count = await get_read_count(db_user["id"], lesson_id)
    await call.message.answer(
        result["text"], parse_mode="HTML",
        reply_markup=lesson_keyboard(lesson_id, read_count=read_count),
    )
    await call.answer()
