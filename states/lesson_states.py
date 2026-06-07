from aiogram.fsm.state import State, StatesGroup

class TestSession(StatesGroup):
    q1_multiple_choice = State()
    q2_translation     = State()
    q3_sentence        = State()
