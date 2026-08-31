from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from database.models import OwnerDecision

def get_start_keyboard() -> InlineKeyboardMarkup:
    """First screen keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Так, почати", callback_data="start_interview"),
                InlineKeyboardButton(text="⏳ Не зараз", callback_data="postpone_interview")
            ]
        ]
    )

def get_terms_keyboard() -> InlineKeyboardMarkup:
    """Terms and compensation model acceptance keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Мене влаштовують умови",
                    callback_data="accept_terms"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Мене не влаштовують",
                    callback_data="decline_terms"
                )
            ]
        ]
    )

def get_voice_skip_keyboard() -> InlineKeyboardMarkup:
    """Optional skip keyboard for voice message step."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⏩ Пропустити голосове", callback_data="skip_voice")
            ]
        ]
    )

def get_admin_candidate_keyboard(candidate_id: int, current_decision: str = "") -> InlineKeyboardMarkup:
    """Admin inline keyboard. Buttons change ONLY owner_decision."""
    buttons = [
        [
            InlineKeyboardButton(
                text=f"{'👉 ' if current_decision == OwnerDecision.INTERVIEW else ''}✅ Взяти на співбесіду",
                callback_data=f"adm_decide:{candidate_id}:{OwnerDecision.INTERVIEW}"
            ),
            InlineKeyboardButton(
                text=f"{'👉 ' if current_decision == OwnerDecision.TEST else ''}🟡 Додатковий тест",
                callback_data=f"adm_decide:{candidate_id}:{OwnerDecision.TEST}"
            )
        ],
        [
            InlineKeyboardButton(
                text=f"{'👉 ' if current_decision == OwnerDecision.REJECTED else ''}❌ Відмовити",
                callback_data=f"adm_decide:{candidate_id}:{OwnerDecision.REJECTED}"
            ),
            InlineKeyboardButton(
                text=f"{'👉 ' if current_decision == OwnerDecision.RESERVE else ''}📌 У резерв",
                callback_data=f"adm_decide:{candidate_id}:{OwnerDecision.RESERVE}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🧠 Чому AI рекомендує",
                callback_data=f"adm_explain:{candidate_id}"
            ),
            InlineKeyboardButton(
                text="📋 5 питань для інтерв'ю",
                callback_data=f"adm_questions:{candidate_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="📝 Всі відповіді",
                callback_data=f"adm_answers:{candidate_id}"
            ),
            InlineKeyboardButton(
                text="🔄 Скинути кандидата",
                callback_data=f"adm_reset:{candidate_id}"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_contact_request_keyboard() -> ReplyKeyboardMarkup:
    """Reply keyboard to share phone number."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Надіслати свій номер телефону", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
