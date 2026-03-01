from aiogram.fsm.state import State, StatesGroup


class CandidateStates(StatesGroup):
    wait_restart_confirmation = State()
    wait_last_name = State()
    wait_first_name = State()
    wait_middle_name = State()
    wait_contacts = State()
    wait_question_answer = State()
    wait_project_link = State()
