from typing import Callable, Awaitable, Any
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from database.repository.users import get_user

class LanguageMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict], Awaitable[Any]],
        event: TelegramObject,
        data: dict,
    ) -> Any:
        user_id = getattr(getattr(event, "from_user", None), "id", None)
        if user_id:
            user = await get_user(user_id)
            data["lang"] = user["language"] if user else "ru"
            data["db_user"] = user
        return await handler(event, data)
