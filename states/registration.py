from aiogram.fsm.state import State, StatesGroup

class Registration(StatesGroup):
    choosing_language = State()
    choosing_time = State()
