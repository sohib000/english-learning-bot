from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from database.db import get_db
from services.lesson_service import get_lesson_message
from keyboards.lessons import lesson_keyboard

router = Router()

async def get_read_count(user_id: int, lesson_id: int) -> int:
    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT read_count FROM progress WHERE user_id=? AND lesson_id=?",
        (user_id, lesson_id)
    )
    await db.close()
    if rows:
        return rows[0]["read_count"] or 0
    return 0

async def increment_read_count(user_id: int, lesson_id: int) -> int:
    db = await get_db()
    await db.execute(
        "INSERT OR IGNORE INTO progress (user_id, lesson_id, read_count) VALUES (?,?,0)",
        (user_id, lesson_id)
    )
    await db.execute(
        "UPDATE progress SET read_count = read_count + 1 WHERE user_id=? AND lesson_id=?",
        (user_id, lesson_id)
    )
    await db.commit()
    rows = await db.execute_fetchall(
        "SELECT MAX(read_count) as rc FROM progress WHERE user_id=? AND lesson_id=?",
        (user_id, lesson_id)
    )
    await db.close()
    return rows[0]["rc"] or 1

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
    lesson_id = int(call.data.split(":")[1])
    lang = db_user["language"] if db_user else "ru"
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
# ══════════════════════════════════════════
@router.callback_query(F.data.startswith("audio:"))
async def send_audio(call: CallbackQuery, db_user: dict):
    import os
    lang = db_user["language"]
    result = await get_lesson_message(
        level=db_user["current_level"],
        lesson_number=db_user["current_lesson"],
        language=lang,
    )

    if not result:
        await call.answer()
        return

    path = result.get("audio_path")

    # Проверяем кэш
    if path and os.path.exists(path) and os.path.getsize(path) > 0:
        audio = FSInputFile(path)
        caption = "🔊 Diqqat bilan tinglang!" if lang == "uz" else "🔊 Слушай внимательно!"
        await call.message.answer_audio(audio, caption=caption)
        await call.answer()
        return

    # Генерируем
    msg_wait = "⏳ Audio tayyorlanmoqda..." if lang == "uz" else "⏳ Генерирую аудио..."
    await call.answer(msg_wait, show_alert=False)

    from services.audio_service import get_or_generate_audio
    try:
        new_path = await get_or_generate_audio(
            result["lesson"]["text_en"], result["lesson"]["id"]
        )
        if new_path and os.path.exists(new_path) and os.path.getsize(new_path) > 0:
            audio = FSInputFile(new_path)
            caption = "🔊 Diqqat bilan tinglang!" if lang == "uz" else "🔊 Слушай внимательно!"
            await call.message.answer_audio(audio, caption=caption)
        else:
            msg = "❌ Audio mavjud emas." if lang == "uz" else "❌ Аудио недоступно на сервере."
            await call.message.answer(msg)
    except Exception:
        msg = "❌ Audio xatosi." if lang == "uz" else "❌ Ошибка аудио."
        await call.message.answer(msg)

    await call.answer()

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
