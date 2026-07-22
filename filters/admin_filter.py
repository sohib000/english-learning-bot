from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from config import ADMIN_IDS

class IsAdmin(BaseFilter):
    async def __call__(self, event) -> bool:
        if isinstance(event, Message):
            return event.from_user.id in ADMIN_IDS
        if isinstance(event, CallbackQuery):
            return event.from_user.id in ADMIN_IDS
        return False
