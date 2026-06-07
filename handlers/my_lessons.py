from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.db import get_db
from database.repository.lessons import load_lesson, get_total_lessons
from keyboards.lessons import lesson_keyboard

router = Router()

async def get_user_progress(user_id: int) -> dict:
    """Возвращает словарь {lesson_id: данные} по всем записям пользователя."""
    db = await get_db()
    rows = await db.execute_fetchall(
        """SELECT lesson_id,
                  MAX(score) as score,
                  MAX(completed) as completed,
                  COALESCE(MAX(read_count), 0) as read_count
           FROM progress
           WHERE user_id = ?
           GROUP BY lesson_id""",
        (user_id,)
    )
    await db.close()
    return {r["lesson_id"]: dict(r) for r in rows}

def lesson_icon(p: dict) -> str:
    if not p or not p.get("completed"):
        return "📤"
    score = p["score"] or 0
    if score >= 80: return "🏆"
    if score >= 60: return "✅"
    return "😐"

async def build_my_lessons_keyboard(user_id: int, current_lesson: int, level: int, lang: str) -> InlineKeyboardMarkup:
    progress = await get_user_progress(user_id)
    rows = []

    # Показываем все уроки от 1 до current_lesson
    for num in range(1, current_lesson + 1):
        lesson = load_lesson(level, num)
        if not lesson:
            continue
        lesson_id = lesson["id"]
        p = progress.get(lesson_id, {})
        icon = lesson_icon(p)
        score = p.get("score") or 0
        rc    = p.get("read_count") or 0

        score_text = f" — {score}%" if p.get("completed") else ""
        read_text  = f" 👁{rc}"    if rc > 0             else ""

        # Текущий урок — пометим
        if num == current_lesson:
            today = " (bugun)" if lang == "uz" else " (сегодня)"
            icon = "📖"
            score_text = today
            read_text  = f" 👁{rc}" if rc > 0 else ""

        rows.append([InlineKeyboardButton(
            text=f"{icon} #{num:03d} {lesson['title']}{score_text}{read_text}",
            callback_data=f"mylessons:open:{num}"
        )])

    rows.append([InlineKeyboardButton(
        text="❌ Yopish" if lang == "uz" else "❌ Закрыть",
        callback_data="mylessons:close"
    )])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def build_header(progress: dict, current_lesson: int, lang: str) -> str:
    done   = sum(1 for p in progress.values() if p.get("completed"))
    total  = current_lesson  # всего уроков включая текущий
    scores = [p["score"] for p in progress.values() if p.get("completed") and p.get("score")]
    avg    = sum(scores) / len(scores) if scores else 0

    legend = "🏆 80%+  ✅ 60%+  😐 60%-  📤 test yo'q  👁 o'qishlar" if lang == "uz" \
             else "🏆 80%+  ✅ 60%+  😐 ниже 60%  📤 без теста  👁 прочтений"

    if lang == "uz":
        return (
            f"📚 <b>Mening darslarim</b>\n\n"
            f"Testdan o'tilgan: <b>{done} / {total}</b>\n"
            f"O'rtacha ball: <b>{avg:.0f}%</b>\n\n"
            f"{legend}"
        )
    return (
        f"📚 <b>Мои уроки</b>\n\n"
        f"Тест сдан: <b>{done} / {total}</b>\n"
        f"Средний балл: <b>{avg:.0f}%</b>\n\n"
        f"{legend}"
    )

# ══════════════════════════════════════════
#  Показать список уроков
# ══════════════════════════════════════════
@router.message(F.text.in_(["📚 Мои уроки", "📚 Mening darslarim"]))
async def show_my_lessons(message: Message, db_user: dict):
    if not db_user:
        await message.answer("Сначала нажми /start")
        return

    lang    = db_user["language"]
    current = db_user["current_lesson"]
    level   = db_user["current_level"]
    progress = await get_user_progress(db_user["id"])
    kb      = await build_my_lessons_keyboard(db_user["id"], current, level, lang)
    header  = build_header(progress, current, lang)
    await message.answer(header, parse_mode="HTML", reply_markup=kb)


# ══════════════════════════════════════════
#  Открыть конкретный урок
# ══════════════════════════════════════════
@router.callback_query(F.data.startswith("mylessons:open:"))
async def open_my_lesson(call: CallbackQuery, db_user: dict):
    lesson_num = int(call.data.split(":")[2])
    lang = db_user["language"]
    level = db_user["current_level"]

    lesson = load_lesson(level, lesson_num)
    if not lesson:
        await call.answer("Урок не найден", show_alert=True)
        return

    lesson_id = lesson["id"]
    lang_key = "text_uz" if lang == "uz" else "text_ru"
    translation = lesson.get(lang_key, "")

    words_lines = []
    for w in lesson["words"]:
        tr = w.get("uz" if lang == "uz" else "ru", "")
        words_lines.append(f"• <b>{w['en']}</b> — {tr}")

    # Прошлый результат и счётчик прочтений
    db = await get_db()
    p_rows = await db.execute_fetchall(
        """SELECT MAX(score) as score, MAX(completed) as completed,
                  COALESCE(MAX(read_count), 0) as read_count
           FROM progress WHERE user_id=? AND lesson_id=?""",
        (db_user["id"], lesson_id)
    )
    await db.close()

    p = dict(p_rows[0]) if p_rows else {}
    info_lines = ""
    try:
        rc = p["read_count"] or 0
        if rc > 0:
            read_label = "Marta o'qilgan" if lang == "uz" else "Раз прочитано"
            info_lines += f"\n👁 {read_label}: <b>{rc}</b>"
        if p["completed"]:
            score = p["score"] or 0
            icon = "🏆" if score >= 80 else "✅" if score >= 60 else "😐"
            result_label = "Oldingi natija" if lang == "uz" else "Лучший результат"
            info_lines += f"\n{icon} {result_label}: <b>{score}%</b>"
    except Exception:
        pass

    translate_label = "Tarjima" if lang == "uz" else "Перевод"
    words_label     = "So'zlar" if lang == "uz" else "Слова"

    text = (
        f"📖 <b>#{lesson_num:03d} {lesson['title']}</b>{info_lines}\n\n"
        f"<b>English:</b>\n{lesson['text_en']}\n\n"
        f"<b>{translate_label}:</b>\n{translation}\n\n"
        f"<b>{words_label}:</b>\n" + "\n".join(words_lines)
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🔊 Audio" if lang == "uz" else "🔊 Аудио",
            callback_data=f"audio:{lesson_id}"
        )],
        [InlineKeyboardButton(
            text=f"✅ O'qidim ({rc if p_rows else 0})" if lang == "uz" else f"✅ Прочитал ({rc if p_rows else 0})",
            callback_data=f"read:{lesson_id}"
        )],
        [InlineKeyboardButton(
            text="📝 Testni topshirish" if lang == "uz" else "📝 Пройти тест",
            callback_data=f"test:{lesson_num}"
        )],
        [InlineKeyboardButton(
            text="◀️ Barcha darslar" if lang == "uz" else "◀️ Все уроки",
            callback_data="mylessons:back"
        )],
    ])

    await call.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await call.answer()


# ══════════════════════════════════════════
#  Назад к списку
# ══════════════════════════════════════════
@router.callback_query(F.data == "mylessons:back")
async def back_to_my_lessons(call: CallbackQuery, db_user: dict):
    lang    = db_user["language"]
    current = db_user["current_lesson"]
    level   = db_user["current_level"]
    progress = await get_user_progress(db_user["id"])
    kb      = await build_my_lessons_keyboard(db_user["id"], current, level, lang)
    header  = build_header(progress, current, lang)
    await call.message.answer(header, parse_mode="HTML", reply_markup=kb)
    await call.answer()

@router.callback_query(F.data == "mylessons:close")
async def close_my_lessons(call: CallbackQuery):
    try:
        await call.message.delete()
    except Exception:
        pass
    await call.answer()