from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.db import get_db
from database.repository.lessons import load_lesson
import os
from config import LESSONS_DIR

router = Router()

async def get_lesson_stats(lesson_id: int) -> dict:
    db = await get_db()
    rows = await db.execute_fetchall(
        """SELECT u.name, u.telegram_id, p.score, p.completed_at, p.lesson_sent
           FROM progress p
           JOIN users u ON u.id = p.user_id
           WHERE p.lesson_id = ?
           ORDER BY p.completed_at DESC""",
        (lesson_id,)
    )
    await db.close()
    return rows

def get_all_lessons() -> list:
    result = []
    for level in range(1, 4):
        path = os.path.join(LESSONS_DIR, f"level_{level}")
        if not os.path.exists(path):
            continue
        files = sorted([f for f in os.listdir(path) if f.endswith(".json")])
        for fname in files:
            lesson_num = int(fname.replace("lesson_", "").replace(".json", ""))
            lesson = load_lesson(level, lesson_num)
            if lesson:
                result.append((level, lesson_num, lesson))
    return result

def lessons_list_keyboard(page: int = 0) -> InlineKeyboardMarkup:
    lessons = get_all_lessons()
    per_page = 8
    start = page * per_page
    end = start + per_page
    page_lessons = lessons[start:end]

    rows = []
    for level, num, lesson in page_lessons:
        rows.append([InlineKeyboardButton(
            text=f"📖 #{num:03d} {lesson['title']}",
            callback_data=f"adm:lesson_detail:{level}:{num}"
        )])

    # Навигация
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"adm:lessons_page:{page-1}"))
    if end < len(lessons):
        nav.append(InlineKeyboardButton(text="Вперёд ▶️", callback_data=f"adm:lessons_page:{page+1}"))
    if nav:
        rows.append(nav)

    rows.append([InlineKeyboardButton(text="🔙 Главное меню", callback_data="adm:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

async def build_lesson_detail(level: int, num: int) -> str:
    lesson = load_lesson(level, num)
    if not lesson:
        return "Урок не найден"

    db = await get_db()
    # Все кто получил урок и прошёл тест
    progress = await db.execute_fetchall(
        """SELECT u.name, p.score, p.completed, p.lesson_sent, p.completed_at
           FROM progress p
           JOIN users u ON u.id = p.user_id
           WHERE p.lesson_id = ?
           ORDER BY p.score DESC""",
        (lesson["id"],)
    )
    await db.close()

    total_sent = sum(1 for r in progress if r["lesson_sent"])
    total_done = sum(1 for r in progress if r["completed"])
    scores = [r["score"] for r in progress if r["completed"]]
    avg_score = sum(scores) / len(scores) if scores else 0

    words_text = ""
    for w in lesson.get("words", [])[:5]:
        words_text += f"  • {w['en']} — {w.get('uz', '')}\n"

    users_text = ""
    if progress:
        users_text = "\n👥 Пользователи:\n"
        for r in progress[:10]:
            if r["completed"]:
                icon = "✅" if r["score"] >= 70 else "😐"
                users_text += f"  {icon} {r['name']} — {r['score']}%\n"
            else:
                users_text += f"  📤 {r['name']} — только получил\n"
    else:
        users_text = "\n👥 Никто ещё не проходил этот урок"

    return (
        f"📖 <b>Урок #{num:03d} — {lesson['title']}</b>\n\n"
        f"📊 <b>Статистика:</b>\n"
        f"  📤 Отправлено: <b>{total_sent}</b> чел.\n"
        f"  ✅ Прошли тест: <b>{total_done}</b> чел.\n"
        f"  🎯 Средний балл: <b>{avg_score:.0f}%</b>\n\n"
        f"📝 <b>Слова (первые 5):</b>\n{words_text}"
        f"{users_text}"
    )
