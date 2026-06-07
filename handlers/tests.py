from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from services.test_service import build_test_sequence
from states.lesson_states import TestSession
from keyboards.tests import choices_keyboard
from database.repository.tests import save_progress
from database.repository.statistics import update_after_test
from database.repository.users import advance_lesson

router = Router()

def safe(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def result_emoji(score: int) -> str:
    if score >= 80: return "🏆"
    if score >= 60: return "👍"
    if score >= 40: return "😐"
    return "💪"

async def send_question(message: Message, state: FSMContext):
    """Отправляет текущий вопрос."""
    data = await state.get_data()
    tests = data["tests"]
    q_index = data["q_index"]
    lang = data.get("lang", "ru")
    total = len(tests)
    q = tests[q_index]

    num_text = f"Savol {q_index + 1} / {total}" if lang == "uz" else f"Вопрос {q_index + 1} / {total}"
    text = f"<b>{num_text}</b>\n\n{q['question']}"

    if q["type"] == "choice":
        kb = choices_keyboard(q["options"], q_index)
        await message.answer(text, parse_mode="HTML", reply_markup=kb)
        await state.set_state(TestSession.q1_multiple_choice)
    else:
        hint = "👆 Javobni yozing:" if lang == "uz" else "👆 Напиши ответ:"
        await message.answer(f"{text}\n\n{hint}", parse_mode="HTML")
        await state.set_state(TestSession.q2_translation)


# ══════════════════════════════════════════
#  Начало теста
# ══════════════════════════════════════════
@router.callback_query(F.data.startswith("test:"))
async def start_test(call: CallbackQuery, state: FSMContext, db_user: dict):
    lesson_id = int(call.data.split(":")[1])
    lang = db_user["language"]

    # Используем lesson_id из кнопки — не current_lesson из БД!
    tests = build_test_sequence(
        db_user["current_level"],
        lesson_id,
        lang,
    )
    if not tests:
        await call.answer("Тест недоступен" if lang == "ru" else "Test mavjud emas", show_alert=True)
        return

    await state.update_data(
        tests=tests,
        q_index=0,
        score=0,
        lesson_id=lesson_id,
        lang=lang,
        user_id=db_user["id"],
        tg_id=call.from_user.id,
    )

    # Удаляем сообщение с уроком
    try:
        await call.message.delete()
    except Exception:
        pass

    # Заголовок
    header = (
        "🧠 <b>Test boshlanmoqda!</b>\n\n"
        "5 ta savol. Har bir savolga diqqat bilan javob bering. 💪"
        if lang == "uz" else
        "🧠 <b>Тест начинается!</b>\n\n"
        "5 вопросов. Читай внимательно каждый вопрос. 💪"
    )
    await call.message.answer(header, parse_mode="HTML")
    await call.answer()
    await send_question(call.message, state)


# ══════════════════════════════════════════
#  Ответ кнопкой
# ══════════════════════════════════════════
@router.callback_query(TestSession.q1_multiple_choice, F.data.startswith("ans:"))
async def handle_choice(call: CallbackQuery, state: FSMContext):
    parts = call.data.split(":")
    answer = parts[2]

    data = await state.get_data()
    q = data["tests"][data["q_index"]]
    correct = q["correct"]
    lang = data.get("lang", "ru")
    is_ok = answer.strip().lower() == correct.strip().lower()

    # Убираем кнопки
    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    # Фидбек
    if is_ok:
        fb = "✅ <b>To'g'ri!</b>" if lang == "uz" else "✅ <b>Верно!</b>"
    else:
        fb = (f"❌ <b>Noto'g'ri.</b>\nTo'g'ri javob: <b>{safe(correct)}</b>"
              if lang == "uz" else
              f"❌ <b>Неверно.</b>\nПравильный ответ: <b>{safe(correct)}</b>")
    await call.message.answer(fb, parse_mode="HTML")
    await call.answer()

    # Обновляем счёт и индекс
    pts = round(100 / len(data["tests"]))
    new_score = data["score"] + (pts if is_ok else 0)
    next_i = data["q_index"] + 1
    await state.update_data(score=new_score, q_index=next_i)

    if next_i < len(data["tests"]):
        await send_question(call.message, state)
    else:
        await finish_test(call.message, state)


# ══════════════════════════════════════════
#  Ответ текстом
# ══════════════════════════════════════════
@router.message(TestSession.q2_translation)
async def handle_text(message: Message, state: FSMContext):
    data = await state.get_data()
    q = data["tests"][data["q_index"]]
    correct = q["correct"]
    lang = data.get("lang", "ru")
    is_ok = message.text.strip().lower() == correct.strip().lower()

    if is_ok:
        fb = "✅ <b>To'g'ri!</b>" if lang == "uz" else "✅ <b>Верно!</b>"
    else:
        fb = (f"❌ <b>Noto'g'ri.</b>\nTo'g'ri javob: <b>{safe(correct)}</b>"
              if lang == "uz" else
              f"❌ <b>Неверно.</b>\nПравильный ответ: <b>{safe(correct)}</b>")
    await message.answer(fb, parse_mode="HTML")

    pts = round(100 / len(data["tests"]))
    new_score = data["score"] + (pts if is_ok else 0)
    next_i = data["q_index"] + 1
    await state.update_data(score=new_score, q_index=next_i)

    if next_i < len(data["tests"]):
        await send_question(message, state)
    else:
        await finish_test(message, state)


# ══════════════════════════════════════════
#  Финал
# ══════════════════════════════════════════
async def finish_test(target: Message, state: FSMContext):
    data = await state.get_data()
    final_score = min(data["score"], 100)
    lang = data.get("lang", "ru")
    emoji = result_emoji(final_score)

    await save_progress(data["user_id"], data["lesson_id"], final_score)
    await update_after_test(data["user_id"], final_score)
    await advance_lesson(data["tg_id"])
    await state.clear()

    if lang == "uz":
        msg1 = "Zo'r natija! Davom eting! 💪" if final_score >= 80 else "Ertaga yanada yaxshi bo'ladi! 🌅"
        text = (
            f"{emoji} <b>Test yakunlandi!</b>\n\n"
            f"Natija: <b>{final_score}%</b>\n\n"
            f"{msg1}\n\n"
            f"Keyingi dars — erta tongda 🌅"
        )
    else:
        msg2 = "Отлично! Так держать! 💪" if final_score >= 80 else "Завтра будет лучше! 🌅"
        text = (
            f"{emoji} <b>Тест завершён!</b>\n\n"
            f"Результат: <b>{final_score}%</b>\n\n"
            f"{msg2}\n\n"
            f"Следующий урок — завтра утром 🌅"
        )
    await target.answer(text, parse_mode="HTML")
