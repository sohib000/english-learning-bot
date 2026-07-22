from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from aiogram.exceptions import TelegramForbiddenError

from filters.admin_filter import IsAdmin
from database.db import get_db
from admin_panel.lessons import get_all_lessons, lessons_list_keyboard, build_lesson_detail
from utils.helpers import clean_name

router = Router()
router.message.filter(IsAdmin())

class AdminState(StatesGroup):
    broadcast_text     = State()
    broadcast_confirm  = State()
    broadcast_filter   = State()
    search_user        = State()

def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Пользователи",  callback_data="adm:users")],
        [InlineKeyboardButton(text="📊 Статистика",    callback_data="adm:stats")],
        [InlineKeyboardButton(text="📚 Все уроки",     callback_data="adm:lessons_page:0")],
        [InlineKeyboardButton(text="📢 Рассылка",      callback_data="adm:broadcast_menu")],
    ])

def back_kb(to: str = "adm:menu") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔙 Назад", callback_data=to)
    ]])

# ══════════════════════════════════════════
#  /admin
# ══════════════════════════════════════════
@router.message(Command("admin"))
async def admin_menu(message: Message):
    await message.answer("🛡️ <b>Админ-панель</b>", parse_mode="HTML", reply_markup=main_menu_kb())

@router.callback_query(F.data == "adm:menu")
async def adm_back_menu(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("🛡️ <b>Админ-панель</b>", parse_mode="HTML", reply_markup=main_menu_kb())
    await call.answer()

# ══════════════════════════════════════════
#  👥 Пользователи — список + поиск
# ══════════════════════════════════════════
@router.callback_query(F.data == "adm:users")
async def adm_users(call: CallbackQuery):
    db = await get_db()
    total  = await db.execute_fetchall("SELECT COUNT(*) as c FROM users")
    today  = await db.execute_fetchall("SELECT COUNT(*) as c FROM users WHERE date(created_at)=date('now')")
    week   = await db.execute_fetchall("SELECT COUNT(*) as c FROM users WHERE created_at >= datetime('now','-7 days')")
    ru     = await db.execute_fetchall("SELECT COUNT(*) as c FROM users WHERE language='ru'")
    uz     = await db.execute_fetchall("SELECT COUNT(*) as c FROM users WHERE language='uz'")
    active = await db.execute_fetchall(
        "SELECT COUNT(DISTINCT user_id) as c FROM progress WHERE completed_at >= datetime('now','-7 days')"
    )
    last5  = await db.execute_fetchall(
        "SELECT name, telegram_id, language, created_at FROM users ORDER BY created_at DESC LIMIT 5"
    )
    await db.close()

    last_text = ""
    for r in last5:
        flag = "🇺🇿" if r["language"] == "uz" else "🇷🇺"
        last_text += f"  {flag} {clean_name(r['name'] or '')} (<code>{r['telegram_id']}</code>)\n"

    text = (
        f"👥 <b>Пользователи</b>\n\n"
        f"📌 Всего: <b>{total[0]['c']}</b>\n"
        f"📅 Сегодня: <b>{today[0]['c']}</b>\n"
        f"📆 За 7 дней: <b>{week[0]['c']}</b>\n"
        f"⚡ Активных (7 дн): <b>{active[0]['c']}</b>\n\n"
        f"🇷🇺 Русский: <b>{ru[0]['c']}</b>\n"
        f"🇺🇿 Узбекский: <b>{uz[0]['c']}</b>\n\n"
        f"🆕 Последние:\n{last_text}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Найти пользователя", callback_data="adm:search_user")],
        [InlineKeyboardButton(text="📋 Все пользователи",   callback_data="adm:users_list:0")],
        [InlineKeyboardButton(text="🔙 Назад",              callback_data="adm:menu")],
    ])
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await call.answer()

@router.callback_query(F.data.startswith("adm:users_list:"))
async def adm_users_list(call: CallbackQuery):
    page = int(call.data.split(":")[2])
    per_page = 8
    offset = page * per_page
    db = await get_db()
    users = await db.execute_fetchall(
        "SELECT name, telegram_id, language, current_lesson FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (per_page, offset)
    )
    total = await db.execute_fetchall("SELECT COUNT(*) as c FROM users")
    await db.close()

    rows = []
    for u in users:
        flag = "🇺🇿" if u["language"] == "uz" else "🇷🇺"
        rows.append([InlineKeyboardButton(
            text=f"{flag} {u['name']} — ур.{u['current_lesson']}",
            callback_data=f"adm:user_detail:{u['telegram_id']}"
        )])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"adm:users_list:{page-1}"))
    if offset + per_page < total[0]["c"]:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"adm:users_list:{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="adm:users")])

    text = f"📋 <b>Все пользователи</b> (стр. {page+1})\nВсего: {total[0]['c']}"
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await call.answer()

# ══════════════════════════════════════════
#  🔍 Поиск пользователя
# ══════════════════════════════════════════
@router.callback_query(F.data == "adm:search_user")
async def adm_search_user(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminState.search_user)
    await call.message.edit_text(
        "🔍 <b>Поиск пользователя</b>\n\nНапиши имя или Telegram ID:",
        parse_mode="HTML",
        reply_markup=back_kb("adm:users")
    )
    await call.answer()

@router.message(AdminState.search_user)
async def adm_search_execute(message: Message, state: FSMContext):
    query = message.text.strip()
    db = await get_db()
    if query.isdigit():
        users = await db.execute_fetchall(
            "SELECT * FROM users WHERE telegram_id=?", (int(query),)
        )
    else:
        users = await db.execute_fetchall(
            "SELECT * FROM users WHERE name LIKE ?", (f"%{query}%",)
        )
    await db.close()

    if not users:
        await message.answer("❌ Пользователь не найден.", reply_markup=back_kb("adm:users"))
        await state.clear()
        return

    rows = [[InlineKeyboardButton(
        text=f"{'🇺🇿' if u['language']=='uz' else '🇷🇺'} {u['name']} ({u['telegram_id']})",
        callback_data=f"adm:user_detail:{u['telegram_id']}"
    )] for u in users]
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="adm:users")])
    await message.answer(
        f"🔍 Найдено: <b>{len(users)}</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )
    await state.clear()

# ══════════════════════════════════════════
#  👤 Детали конкретного пользователя
# ══════════════════════════════════════════
@router.callback_query(F.data.startswith("adm:user_detail:"))
async def adm_user_detail(call: CallbackQuery):
    tg_id = int(call.data.split(":")[2])
    db = await get_db()
    user = await db.execute_fetchall("SELECT * FROM users WHERE telegram_id=?", (tg_id,))
    if not user:
        await call.answer("Не найден", show_alert=True)
        return
    u = dict(user[0])

    stats = await db.execute_fetchall("SELECT * FROM statistics WHERE user_id=?", (u["id"],))
    progress = await db.execute_fetchall(
        "SELECT COUNT(*) as done, MAX(score) as best FROM progress WHERE user_id=? AND completed=TRUE",
        (u["id"],)
    )
    last_activity = await db.execute_fetchall(
        "SELECT MAX(completed_at) as last FROM progress WHERE user_id=?", (u["id"],)
    )
    await db.close()

    s = dict(stats[0]) if stats else {}
    p = dict(progress[0]) if progress else {}
    last = last_activity[0]["last"] if last_activity else "—"

    flag = "🇺🇿" if u["language"] == "uz" else "🇷🇺"
    name = clean_name(u["name"] or "")
    text = (
        f"👤 <b>{name}</b> {flag}\n\n"
        f"🆔 ID: <code>{u['telegram_id']}</code>\n"
        f"⏰ Время урока: <b>{u['notify_time'] or '—'}</b>\n"
        f"📖 Текущий урок: <b>#{u['current_lesson']}</b>\n"
        f"📅 Регистрация: <b>{u['created_at'][:10]}</b>\n"
        f"🕐 Последняя активность: <b>{str(last)[:10] if last else '—'}</b>\n\n"
        f"📊 <b>Статистика:</b>\n"
        f"  🔥 Серия: <b>{s.get('current_streak', 0)} дн.</b>\n"
        f"  📚 Слов: <b>{s.get('words_learned', 0)}</b>\n"
        f"  ✅ Уроков пройдено: <b>{p.get('done', 0)}</b>\n"
        f"  🎯 Лучший балл: <b>{p.get('best', 0)}%</b>\n"
        f"  📈 Средний балл: <b>{s.get('average_score', 0):.0f}%</b>\n"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Написать пользователю", callback_data=f"adm:msg_user:{tg_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="adm:users")],
    ])
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await call.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await call.answer()

@router.callback_query(F.data.startswith("adm:msg_user:"))
async def adm_msg_user_start(call: CallbackQuery, state: FSMContext):
    tg_id = int(call.data.split(":")[2])
    await state.update_data(target_user=tg_id)
    await state.set_state(AdminState.broadcast_text)
    await call.message.edit_text(
        f"✍️ Напиши сообщение для пользователя <code>{tg_id}</code>:",
        parse_mode="HTML",
        reply_markup=back_kb(f"adm:user_detail:{tg_id}")
    )
    await call.answer()

# ══════════════════════════════════════════
#  📊 Статистика
# ══════════════════════════════════════════
@router.callback_query(F.data == "adm:stats")
async def adm_stats(call: CallbackQuery):
    db = await get_db()
    lessons_done  = await db.execute_fetchall("SELECT COUNT(*) as c FROM progress WHERE completed=TRUE")
    avg           = await db.execute_fetchall("SELECT ROUND(AVG(score),1) as a FROM progress WHERE completed=TRUE")
    words         = await db.execute_fetchall("SELECT SUM(words_learned) as s FROM statistics")
    today_active  = await db.execute_fetchall(
        "SELECT COUNT(DISTINCT user_id) as c FROM progress WHERE date(completed_at)=date('now')"
    )
    top_streak    = await db.execute_fetchall(
        "SELECT u.name, s.current_streak FROM statistics s JOIN users u ON u.id=s.user_id ORDER BY s.current_streak DESC LIMIT 3"
    )
    top_lessons   = await db.execute_fetchall(
        "SELECT u.name, s.lessons_completed, s.average_score FROM statistics s JOIN users u ON u.id=s.user_id ORDER BY s.lessons_completed DESC LIMIT 5"
    )
    score_dist    = await db.execute_fetchall(
        """SELECT
            SUM(CASE WHEN score>=80 THEN 1 ELSE 0 END) as excellent,
            SUM(CASE WHEN score>=60 AND score<80 THEN 1 ELSE 0 END) as good,
            SUM(CASE WHEN score<60 THEN 1 ELSE 0 END) as poor
           FROM progress WHERE completed=TRUE"""
    )
    await db.close()

    streak_text = ""
    for i, r in enumerate(top_streak, 1):
        streak_text += f"  {i}. {r['name']} — 🔥{r['current_streak']} дн.\n"

    top_text = ""
    for i, r in enumerate(top_lessons, 1):
        top_text += f"  {i}. {r['name']} — {r['lessons_completed']} ур. ({r['average_score']:.0f}%)\n"

    sd = dict(score_dist[0]) if score_dist else {}
    text = (
        f"📊 <b>Статистика бота</b>\n\n"
        f"👥 Активных сегодня: <b>{today_active[0]['c']}</b>\n"
        f"📚 Уроков пройдено: <b>{lessons_done[0]['c']}</b>\n"
        f"🎯 Средний балл: <b>{avg[0]['a'] or 0}%</b>\n"
        f"📝 Слов изучено: <b>{words[0]['s'] or 0}</b>\n\n"
        f"📈 <b>Результаты тестов:</b>\n"
        f"  🏆 Отлично (80%+): <b>{sd.get('excellent', 0)}</b>\n"
        f"  ✅ Хорошо (60-79%): <b>{sd.get('good', 0)}</b>\n"
        f"  😐 Слабо (<60%): <b>{sd.get('poor', 0)}</b>\n\n"
        f"🔥 <b>Топ серии:</b>\n{streak_text or '—'}\n"
        f"🏆 <b>Топ по урокам:</b>\n{top_text or '—'}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="adm:stats")],
        [InlineKeyboardButton(text="🔙 Назад",    callback_data="adm:menu")],
    ])
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception as e:
        import logging
        logging.error(f"adm_stats error: {e}")
        await call.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await call.answer()

# ══════════════════════════════════════════
#  📚 Уроки
# ══════════════════════════════════════════
@router.callback_query(F.data.startswith("adm:lessons_page:"))
async def adm_lessons_list(call: CallbackQuery):
    page = int(call.data.split(":")[2])
    lessons = get_all_lessons()
    text = f"📚 <b>Все уроки</b>\nВсего: <b>{len(lessons)}</b>"
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=lessons_list_keyboard(page))
    except Exception:
        await call.message.answer(text, parse_mode="HTML", reply_markup=lessons_list_keyboard(page))
    await call.answer()

@router.callback_query(F.data.startswith("adm:lesson_detail:"))
async def adm_lesson_detail(call: CallbackQuery):
    parts = call.data.split(":")
    level, num = int(parts[2]), int(parts[3])
    text = await build_lesson_detail(level, num)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔙 К списку", callback_data="adm:lessons_page:0")
    ]])
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await call.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await call.answer()

# ══════════════════════════════════════════
#  📢 Рассылка — меню
# ══════════════════════════════════════════
@router.callback_query(F.data == "adm:broadcast_menu")
async def adm_broadcast_menu(call: CallbackQuery):
    db = await get_db()
    total = await db.execute_fetchall("SELECT COUNT(*) as c FROM users")
    ru    = await db.execute_fetchall("SELECT COUNT(*) as c FROM users WHERE language='ru'")
    uz    = await db.execute_fetchall("SELECT COUNT(*) as c FROM users WHERE language='uz'")
    await db.close()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"📢 Всем ({total[0]['c']} чел.)",
            callback_data="adm:broadcast:all"
        )],
        [InlineKeyboardButton(
            text=f"🇷🇺 Только русским ({ru[0]['c']} чел.)",
            callback_data="adm:broadcast:ru"
        )],
        [InlineKeyboardButton(
            text=f"🇺🇿 Только узбекским ({uz[0]['c']} чел.)",
            callback_data="adm:broadcast:uz"
        )],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="adm:menu")],
    ])
    await call.message.edit_text(
        "📢 <b>Рассылка</b>\n\nВыбери кому отправить:",
        parse_mode="HTML", reply_markup=kb
    )
    await call.answer()

@router.callback_query(F.data.startswith("adm:broadcast:"))
async def adm_broadcast_start(call: CallbackQuery, state: FSMContext):
    target = call.data.split(":")[2]
    await state.update_data(broadcast_target=target, target_user=None)
    await state.set_state(AdminState.broadcast_text)

    labels = {"all": "всем", "ru": "русскоязычным", "uz": "узбекоязычным"}
    await call.message.edit_text(
        f"✍️ <b>Рассылка {labels.get(target, '')} </b>\n\nНапиши текст сообщения:",
        parse_mode="HTML",
        reply_markup=back_kb("adm:broadcast_menu")
    )
    await call.answer()

@router.message(AdminState.broadcast_text)
async def adm_broadcast_preview(message: Message, state: FSMContext):
    await state.update_data(broadcast_text=message.text)
    data = await state.get_data()
    target = data.get("broadcast_target", "all")
    target_user = data.get("target_user")

    db = await get_db()
    if target_user:
        count = 1
        label = f"пользователю <code>{target_user}</code>"
    elif target == "ru":
        r = await db.execute_fetchall("SELECT COUNT(*) as c FROM users WHERE language='ru'")
        count = r[0]["c"]
        label = "русскоязычным"
    elif target == "uz":
        r = await db.execute_fetchall("SELECT COUNT(*) as c FROM users WHERE language='uz'")
        count = r[0]["c"]
        label = "узбекоязычным"
    else:
        r = await db.execute_fetchall("SELECT COUNT(*) as c FROM users")
        count = r[0]["c"]
        label = "всем"
    await db.close()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Отправить", callback_data="adm:broadcast_send"),
            InlineKeyboardButton(text="❌ Отмена",    callback_data="adm:broadcast_cancel"),
        ]
    ])
    await message.answer(
        f"📋 <b>Предпросмотр:</b>\n\n{message.text}\n\n"
        f"📤 Отправить {label}: <b>{count} чел.</b>",
        parse_mode="HTML", reply_markup=kb
    )
    await state.set_state(AdminState.broadcast_confirm)

@router.callback_query(AdminState.broadcast_confirm, F.data == "adm:broadcast_send")
async def adm_broadcast_send(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    text = data.get("broadcast_text", "")
    target = data.get("broadcast_target", "all")
    target_user = data.get("target_user")
    await state.clear()

    db = await get_db()
    if target_user:
        users = [{"telegram_id": target_user}]
    elif target == "ru":
        users = await db.execute_fetchall("SELECT telegram_id FROM users WHERE language='ru'")
    elif target == "uz":
        users = await db.execute_fetchall("SELECT telegram_id FROM users WHERE language='uz'")
    else:
        users = await db.execute_fetchall("SELECT telegram_id FROM users")
    await db.close()

    import asyncio
    sent = failed = 0
    await call.message.edit_text(f"⏳ Отправляю... (0 / {len(users)})")
    for i, user in enumerate(users):
        try:
            await call.bot.send_message(user["telegram_id"], text)
            sent += 1
        except TelegramForbiddenError:
            failed += 1
        except Exception:
            failed += 1
        # Rate limit: не более 25 сообщений/сек
        if (i + 1) % 25 == 0:
            await asyncio.sleep(1)
        if i % 10 == 0 and i > 0:
            try:
                await call.message.edit_text(f"⏳ Отправляю... ({i} / {len(users)})")
            except Exception:
                pass

    await call.message.answer(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"📤 Отправлено: <b>{sent}</b>\n"
        f"❌ Не доставлено: <b>{failed}</b>",
        parse_mode="HTML",
        reply_markup=main_menu_kb()
    )
    await call.answer()

@router.callback_query(F.data == "adm:broadcast_cancel")
async def adm_broadcast_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("🛡️ <b>Админ-панель</b>", parse_mode="HTML", reply_markup=main_menu_kb())
    await call.answer()