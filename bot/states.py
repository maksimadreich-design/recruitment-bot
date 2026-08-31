from aiogram.fsm.state import State, StatesGroup

class RecruitmentStates(StatesGroup):
    waiting_start_confirm = State()
    waiting_terms_acceptance = State()
    waiting_name = State()
    waiting_phone = State()
    answering_questions = State()
    waiting_voice = State()
