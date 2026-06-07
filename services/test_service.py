import random
from database.repository.lessons import load_lesson

DISTRACTORS_EN = [
    "house", "table", "window", "water", "time", "city", "road",
    "book", "door", "night", "green", "happy", "small", "phone",
    "money", "sleep", "chair", "cloud", "stone", "bread", "light"
]
DISTRACTORS_UZ = [
    "uy", "stol", "deraza", "suv", "kitob", "eshik", "pul", "non",
    "tun", "yashil", "baxtli", "kichik", "telefon", "uxlamoq", "bulut"
]
DISTRACTORS_RU = [
    "дом", "стол", "окно", "вода", "книга", "дверь", "деньги", "хлеб",
    "ночь", "зелёный", "счастливый", "маленький", "телефон", "спать", "облако"
]

def _get_5_options(correct: str, pool: list, extra: list) -> list:
    wrong = [w for w in pool if w.lower() != correct.lower()]
    for d in extra:
        if d.lower() not in [w.lower() for w in wrong] and d.lower() != correct.lower():
            wrong.append(d)
    wrong = random.sample(wrong, min(4, len(wrong)))
    options = wrong + [correct]
    random.shuffle(options)
    return options

def build_en_from_translation(lesson: dict, language: str) -> dict:
    """Дан перевод → найди английское слово (5 кнопок)."""
    words = lesson["words"]
    target = random.choice(words)
    tr = target.get(language, target.get("uz", ""))
    correct = target["en"]
    pool_en = [w["en"] for w in words]
    options = _get_5_options(correct, pool_en, DISTRACTORS_EN)
    q = (f'🔤 So\'zni inglizcha toping:\n\n❓ <b>"{tr}"</b>'
         if language == "uz" else
         f'🔤 Найди слово по-английски:\n\n❓ <b>"{tr}"</b>')
    return {"type": "choice", "question": q, "options": options, "correct": correct}

def build_translation_from_en(lesson: dict, language: str) -> dict:
    """Дано английское → найди перевод (5 кнопок)."""
    words = lesson["words"]
    target = random.choice(words)
    correct = target.get(language, target.get("uz", ""))
    pool_tr = [w.get(language, w.get("uz", "")) for w in words]
    extra = DISTRACTORS_UZ if language == "uz" else DISTRACTORS_RU
    options = _get_5_options(correct, pool_tr, extra)
    q = (f'🔄 Tarjimani toping:\n\n❓ <b>"{target["en"]}"</b>'
         if language == "uz" else
         f'🔄 Найди перевод:\n\n❓ <b>"{target["en"]}"</b>')
    return {"type": "choice", "question": q, "options": options, "correct": correct}

def build_fill_blank(lesson: dict, language: str) -> dict:
    """Заполни пропуск в предложении (5 кнопок)."""
    words = lesson["words"]
    sentence = lesson["text_en"]
    found = None
    for w in random.sample(words, len(words)):
        if w["en"].lower() in sentence.lower():
            found = w
            break
    if not found:
        found = random.choice(words)
    correct = found["en"]
    blanked = sentence.lower().replace(correct.lower(), "______", 1)
    pool_en = [w["en"] for w in words]
    options = _get_5_options(correct, pool_en, DISTRACTORS_EN)
    q = (f'📝 Bo\'sh joyni to\'ldiring:\n\n<i>"{blanked}"</i>'
         if language == "uz" else
         f'📝 Заполни пропуск:\n\n<i>"{blanked}"</i>')
    return {"type": "choice", "question": q, "options": options, "correct": correct}

def build_odd_one_out(lesson: dict, language: str) -> dict:
    """Какое слово лишнее? (5 кнопок — 4 из урока + 1 чужое)."""
    words = lesson["words"]
    if len(words) < 4:
        return build_en_from_translation(lesson, language)
    chosen = random.sample(words, 4)
    extra_pool = DISTRACTORS_EN if language == "uz" else DISTRACTORS_EN
    odd = random.choice([d for d in extra_pool
                         if d not in [w["en"] for w in chosen]])
    correct = odd
    options = [w["en"] for w in chosen] + [odd]
    random.shuffle(options)
    q = (f'🚫 Qaysi so\'z bu mavzudan EMAS?\n\n(Mavzu: <b>{lesson["title"]}</b>)'
         if language == "uz" else
         f'🚫 Какое слово НЕ относится к теме?\n\n(Тема: <b>{lesson["title"]}</b>)')
    return {"type": "choice", "question": q, "options": options, "correct": correct}

def build_sentence_builder(lesson: dict, language: str) -> dict:
    """Собери короткое предложение — только первые 5 слов."""
    sentence = lesson["text_en"].split(".")[0].strip()  # только первое предложение
    words_list = sentence.split()
    # Берём первые 5 слов чтобы не было каши
    if len(words_list) > 5:
        words_list = words_list[:5]
        sentence = " ".join(words_list)
    shuffled = words_list.copy()
    while shuffled == words_list:
        random.shuffle(shuffled)
    q = (f'🔀 Gapni tuzin (birinchi 5 so\'z):\n\n<b>{" / ".join(shuffled)}</b>'
         if language == "uz" else
         f'🔀 Собери предложение (первые 5 слов):\n\n<b>{" / ".join(shuffled)}</b>')
    return {"type": "text", "question": q, "correct": sentence.lower()}

def build_test_sequence(level: int, lesson_number: int, language: str) -> list:
    lesson = load_lesson(level, lesson_number)
    if not lesson:
        return []

    # Фиксированный порядок: 3 с кнопками → 1 текст → 1 с кнопками
    return [
        build_en_from_translation(lesson, language),   # Q1 — кнопки
        build_translation_from_en(lesson, language),   # Q2 — кнопки
        build_fill_blank(lesson, language),             # Q3 — кнопки
        build_sentence_builder(lesson, language),       # Q4 — текст
        build_odd_one_out(lesson, language),            # Q5 — кнопки
    ]