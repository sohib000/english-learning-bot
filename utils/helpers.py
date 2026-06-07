import re

def safe_html(text: str) -> str:
    """Экранирует HTML спецсимволы."""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))

def clean_name(name: str) -> str:
    """Убирает эмодзи и спецсимволы из имени, оставляет только текст."""
    if not name:
        return "друг"
    # Убираем эмодзи
    emoji_pattern = re.compile(
        "[\U00010000-\U0010ffff"
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE
    )
    cleaned = emoji_pattern.sub("", name).strip()
    # Экранируем HTML
    cleaned = safe_html(cleaned)
    return cleaned if cleaned else "друг"