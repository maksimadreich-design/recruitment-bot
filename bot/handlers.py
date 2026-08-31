import logging
from datetime import datetime
from typing import Dict, Any
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from config import config
from database.db import db
from database.models import OwnerDecision
from questions.questions_data import QUESTIONS, VOICE_TASK_PROMPT
from ai.analyzer import ai_analyzer
from utils.keyboards import (
    get_start_keyboard,
    get_terms_keyboard,
    get_voice_skip_keyboard,
    get_admin_candidate_keyboard,
    get_contact_request_keyboard
)
from utils.formatters import format_admin_candidate_card
from bot.states import RecruitmentStates

logger = logging.getLogger(__name__)
bot_router = Router()

WELCOME_TEXT = (
    "Привіт 👋\n\n"
    "Ми шукаємо менеджерів з холодних продажів у digital-команду.\n\n"
    "Твоя задача — спілкуватися з власниками бізнесів, знаходити їхні потреби та пропонувати рішення, "
    "які допомагають отримувати більше клієнтів і автоматизувати роботу.\n\n"
    "Досвід у продажах буде плюсом, але не є обов'язковим.\n\n"
    "Первинний відбір займає приблизно 5–10 хвилин.\n\n"
    "Готовий/а пройти відбір?"
)

TERMS_TEXT = (
    "━━━━━━━━━━━━━━━━━━━━\n"
    "💼 <b>УМОВИ РОБОТИ</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "Ми шукаємо менеджерів з продажу digital-послуг.\n\n"
    "🌐 <b>ЩО МИ ПРОДАЄМО:</b>\n\n"
    "• Розробка сайтів — <b>10 000–30 000 грн</b>\n"
    "• SEO — <b>7 000 грн</b>\n"
    "• Автоматизації — <b>від 6 000 грн</b>\n\n"
    "<i>Telegram-боти за 700 грн НЕ є основним напрямком роботи менеджерів.</i>\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "💰 <b>СИСТЕМА КОМІСІЇ</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "Оплата залежить від результату.\n\n"
    "<b>Фіксованої ставки немає.</b>\n\n"
    "<b>1 закритий клієнт</b>\n"
    "→ <b>35%</b>\n\n"
    "<b>2–4 закритих клієнти</b>\n"
    "→ <b>40%</b>\n\n"
    "<b>5+ закритих клієнтів</b>\n"
    "→ <b>45%</b>\n\n"
    "Відсоток визначається за загальною кількістю закритих клієнтів у поточному календарному місяці.\n\n"
    "<b>Після досягнення нового рівня комісії він застосовується до всіх продажів поточного місяця.</b>\n\n"
    "Якщо клієнт платить частинами — комісія виплачується пропорційно фактично отриманим платежам.\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "🔥 <b>БОНУС ЗА АКТИВНІСТЬ</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "Протягом робочого тижня потрібно зробити <b>40+ підтверджених холодних контактів</b>.\n\n"
    "Виконали норму?\n"
    "→ На наступний тиждень активується бонус.\n\n"
    "За <b>КОЖНОГО</b> клієнта, якого ви закриєте наступного тижня:\n"
    "💰 <b>+1 000 грн додатково.</b>\n\n"
    "<i>Приклад:</i>\n"
    "40+ контактів цього тижня\n"
    "↓\n"
    "бонус активований наступного тижня\n"
    "↓\n"
    "3 клієнти = <b>+3 000 грн</b>\n"
    "↓\n"
    "5 клієнтів = <b>+5 000 грн</b>\n\n"
    "Якщо наступного тижня знову виконати норму 40+ контактів — бонус продовжується.\n\n"
    "Якщо норму не виконати — бонус на наступний тиждень не активується. Бонус не накопичується.\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "🏆 <b>ДОДАТКОВІ МОЖЛИВОСТІ</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "🥇 <b>Найкращий менеджер місяця:</b>\n"
    "<b>+5 000 грн бонусу.</b>\n\n"
    "👑 <b>Team Lead:</b>\n"
    "Після <b>20 закритих клієнтів</b> менеджер може претендувати на позицію Team Lead.\n\n"
    "Team Lead отримує:\n"
    "• можливість керувати командою;\n"
    "• <b>+5% від продажів</b> менеджерів своєї команди;\n"
    "• можливість отримувати додаткові командні бонуси.\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "📞 <b>ФОРМАТ РОБОТИ</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "🏠 Віддалена робота\n"
    "📅 Графік: <b>2/2</b>\n"
    "⏰ Робочий час: <b>10:00–17:00</b>\n"
    "📞 Робота з холодними клієнтами\n"
    "🔎 Менеджер самостійно знаходить потенційних клієнтів.\n"
    "📱 Дзвінки здійснюються зі свого номера.\n"
    "🎯 Основний показник активності: <b>40+ підтверджених холодних контактів на тиждень</b>.\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "🎓 <b>НАВЧАННЯ</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "Навчання повністю безкоштовне.\n"
    "Тривалість: <b>2–4 дні</b>.\n\n"
    "Під час навчання оплата НЕ нараховується.\n"
    "Після навчання кандидат проходить тест.\n"
    "До роботи з реальними клієнтами допускаються кандидати, які успішно пройшли тест.\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "⚠️ <b>ВАЖЛИВО</b>\n\n"
    "Ця вакансія орієнтована на людей, які готові працювати на результат. "
    "Дохід напряму залежить від кількості та вартості закритих клієнтів.\n\n"
    "Перед початком відбору переконайтеся, що вам підходять формат роботи, система оплати та графік."
)

@bot_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    # Anti-spam check
    existing = await db.get_candidate_by_tg_id(user_id)
    if existing and existing.score is not None:
        await message.answer("Ви вже проходили первинний відбір. Ваша заявка передана менеджеру.")
        return

    await state.clear()
    await message.answer(WELCOME_TEXT, reply_markup=get_start_keyboard())
    await state.set_state(RecruitmentStates.waiting_start_confirm)

@bot_router.callback_query(F.data == "start_interview")
async def cb_start_interview(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    
    user = callback.from_user
    await db.create_or_start_candidate(
        telegram_id=user.id,
        username=user.username,
        name=user.full_name
    )

    await state.update_data(answers={}, retry_counts={}, terms_accepted=False)
    
    # Show TERMS screen first
    await callback.message.answer(
        TERMS_TEXT,
        reply_markup=get_terms_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(RecruitmentStates.waiting_terms_acceptance)

@bot_router.callback_query(F.data == "postpone_interview")
async def cb_postpone_interview(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "Зрозумів! Коли будете готові, просто надішліть команду /start."
    )
    await state.clear()

@bot_router.callback_query(RecruitmentStates.waiting_terms_acceptance, F.data == "accept_terms")
async def cb_accept_terms(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Умови прийнято!")
    await callback.message.edit_reply_markup(reply_markup=None)
    
    user_id = callback.from_user.id
    now_dt = datetime.now().strftime("%d.%m.%Y %H:%M")
    await db.record_terms_acceptance(user_id, accepted=True)
    await state.update_data(terms_accepted=True, terms_accepted_at=now_dt)

    await callback.message.answer(
        "Чудово! Давайте познайомимось 🤝\n\n"
        "Як вас звати? (Введіть ваше ім'я та прізвище):"
    )
    await state.set_state(RecruitmentStates.waiting_name)

@bot_router.callback_query(RecruitmentStates.waiting_terms_acceptance, F.data == "decline_terms")
async def cb_decline_terms(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    
    user_id = callback.from_user.id
    await db.record_terms_acceptance(user_id, accepted=False)
    await state.clear()

    await callback.message.answer(
        "Розуміємо.\n\n"
        "Дякуємо за інтерес до вакансії. Якщо формат роботи або система оплати вам не підходять, проходити відбір не потрібно."
    )

@bot_router.message(RecruitmentStates.waiting_name, F.text)
async def process_name(message: Message, state: FSMContext):
    data = await state.get_data()
    if not data.get("terms_accepted"):
        await message.answer(
            "Будь ласка, спочатку ознайомтесь та погодьтеся з умовами роботи:",
            reply_markup=get_terms_keyboard()
        )
        await state.set_state(RecruitmentStates.waiting_terms_acceptance)
        return

    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Будь ласка, введіть коректне ім'я:")
        return

    await state.update_data(name=name)
    await message.answer(
        f"Приємно познайомитись, {name}! 👍\n\n"
        "Вкажіть ваш контактний номер телефону (можна ввести текстом або натиснути кнопку нижче):",
        reply_markup=get_contact_request_keyboard()
    )
    await state.set_state(RecruitmentStates.waiting_phone)

@bot_router.message(RecruitmentStates.waiting_phone)
async def process_phone(message: Message, state: FSMContext):
    data = await state.get_data()
    if not data.get("terms_accepted"):
        await message.answer(
            "Будь ласка, спочатку ознайомтесь та погодьтеся з умовами роботи:",
            reply_markup=get_terms_keyboard()
        )
        await state.set_state(RecruitmentStates.waiting_terms_acceptance)
        return

    phone = ""
    if message.contact:
        phone = message.contact.phone_number
    elif message.text:
        phone = message.text.strip()
        if len(phone) < 6:
            await message.answer("Будь ласка, введіть дійсний номер телефону:")
            return
    else:
        await message.answer("Будь ласка, надішліть номер телефону текстом або скористайтесь кнопкою:")
        return

    await state.update_data(phone=phone, current_q_idx=0)
    await message.answer("Дякую! Переходимо до запитань 🚀", reply_markup=ReplyKeyboardRemove())
    
    # Send Question 1
    q1 = QUESTIONS[0]
    await message.answer(
        f"<b>1/{len(QUESTIONS)}</b>\n\n{q1.text}",
        parse_mode="HTML"
    )
    await state.set_state(RecruitmentStates.answering_questions)

@bot_router.message(RecruitmentStates.answering_questions, F.text)
async def process_question_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    if not data.get("terms_accepted"):
        await message.answer(
            "Будь ласка, спочатку ознайомтесь та погодьтеся з умовами роботи:",
            reply_markup=get_terms_keyboard()
        )
        await state.set_state(RecruitmentStates.waiting_terms_acceptance)
        return

    current_idx = data.get("current_q_idx", 0)
    answers: Dict[str, str] = data.get("answers", {})
    retry_counts: Dict[str, int] = data.get("retry_counts", {})
    
    user_text = message.text.strip()
    current_q = QUESTIONS[current_idx]
    q_key = f"Q{current_q.id}"

    # Prompt clarification once if answer is too short
    if len(user_text) < 4 and retry_counts.get(q_key, 0) < 1:
        retry_counts[q_key] = 1
        await state.update_data(retry_counts=retry_counts)
        await message.answer(
            "Будь ласка, напишіть трохи детальніше, щоб ми могли краще зрозуміти вашу відповідь 🙏"
        )
        return

    answers[q_key] = user_text
    next_idx = current_idx + 1
    await state.update_data(answers=answers, current_q_idx=next_idx)

    if next_idx < len(QUESTIONS):
        next_q = QUESTIONS[next_idx]
        await message.answer(
            f"<b>{next_idx + 1}/{len(QUESTIONS)}</b>\n\n{next_q.text}",
            parse_mode="HTML"
        )
    else:
        # Move to Voice Task
        await message.answer(
            f"<b>Практичне завдання 🎙</b>\n\n{VOICE_TASK_PROMPT}",
            reply_markup=get_voice_skip_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(RecruitmentStates.waiting_voice)

@bot_router.message(RecruitmentStates.answering_questions)
async def process_non_text_answer(message: Message):
    await message.answer("Будь ласка, надішліть вашу відповідь текстовим повідомленням ✍️")

@bot_router.message(RecruitmentStates.waiting_voice, F.voice | F.audio)
async def process_voice_submission(message: Message, state: FSMContext):
    voice_file_id = message.voice.file_id if message.voice else message.audio.file_id
    await complete_recruitment(message, state, voice_file_id=voice_file_id)

@bot_router.callback_query(RecruitmentStates.waiting_voice, F.data == "skip_voice")
async def process_skip_voice(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await complete_recruitment(callback.message, state, voice_file_id=None, candidate_user=callback.from_user)

async def complete_recruitment(
    message: Message,
    state: FSMContext,
    voice_file_id: str = None,
    candidate_user = None
):
    """
    Analyze answers, save to DB with owner_decision='PENDING', notify admins.
    The candidate receives only a polite confirmation message without AI scores or recommendations.
    """
    data = await state.get_data()
    user = candidate_user or message.from_user
    
    name = data.get("name", user.full_name)
    phone = data.get("phone", "")
    answers = data.get("answers", {})
    terms_accepted = data.get("terms_accepted", True)
    terms_accepted_at = data.get("terms_accepted_at", datetime.now().strftime("%d.%m.%Y %H:%M"))
    has_voice = bool(voice_file_id)

    status_msg = await message.answer("Дякуємо! Зберігаємо ваші відповіді...")

    # Run AI evaluation
    analysis = await ai_analyzer.analyze(
        candidate_name=name,
        answers=answers,
        has_voice=has_voice
    )

    total_score = analysis.get("total_score", 70)
    sales_score = analysis.get("sales_potential_score", total_score)
    sales_level = analysis.get("sales_potential_level", "HIGH")
    ai_recommendation = analysis.get("ai_recommendation", "POTENTIAL")
    ai_reason = analysis.get("ai_recommendation_reason", "")
    confidence = analysis.get("confidence", "HIGH")

    # Save to DB. NOTE: owner_decision is ALWAYS PENDING upon submission!
    candidate = await db.save_candidate_full_assessment(
        telegram_id=user.id,
        name=name,
        phone=phone,
        answers=answers,
        voice_file_id=voice_file_id,
        score=total_score,
        sales_potential_score=sales_score,
        sales_potential_level=sales_level,
        category_scores=analysis.get("category_scores", {}),
        ai_recommendation=ai_recommendation,
        ai_recommendation_reason=ai_reason,
        confidence=confidence,
        strengths=analysis.get("strengths", []),
        weaknesses=analysis.get("weaknesses", []),
        red_flags=analysis.get("red_flags", []),
        positive_signals=analysis.get("positive_signals", []),
        q8_breakdown=analysis.get("q8_breakdown", {}),
        voice_analysis=analysis.get("voice_analysis", {}),
        authenticity_signal=analysis.get("authenticity_signal", "HIGH"),
        interview_questions=analysis.get("interview_questions", []),
        ai_explanation=analysis.get("ai_explanation", {}),
        psychological_profile=analysis.get("psychological_profile", ""),
        predicted_performance=analysis.get("predicted_performance", ""),
        terms_accepted=terms_accepted,
        terms_accepted_at=terms_accepted_at
    )

    # Notify Admins with full structured card
    await notify_admins(message.bot, candidate, voice_file_id)

    # Reply to candidate (strictly neutral without scores or internal AI recommendations)
    await status_msg.edit_text(
        "Дякуємо за проходження первинного відбору.\n\n"
        "Ми переглянемо вашу заявку та зв'яжемося з вами щодо наступного етапу."
    )
    await state.clear()

async def notify_admins(bot, candidate, voice_file_id: str = None):
    """Sends candidate card and attached voice message to all admins."""
    card_text = format_admin_candidate_card(candidate)
    admin_kb = get_admin_candidate_keyboard(candidate.candidate_id, candidate.owner_decision)

    for admin_id in config.ADMIN_IDS:
        try:
            if len(card_text) <= 4000:
                await bot.send_message(
                    chat_id=admin_id,
                    text=card_text,
                    reply_markup=admin_kb,
                    parse_mode="HTML"
                )
            else:
                chunks = [card_text[i:i+3800] for i in range(0, len(card_text), 3800)]
                for idx, chunk in enumerate(chunks):
                    kb = admin_kb if idx == len(chunks) - 1 else None
                    await bot.send_message(
                        chat_id=admin_id,
                        text=chunk,
                        reply_markup=kb,
                        parse_mode="HTML"
                    )

            if voice_file_id:
                await bot.send_voice(
                    chat_id=admin_id,
                    voice=voice_file_id,
                    caption=f"🎙 Голосовий тест: {candidate.name} (#{candidate.candidate_id})"
                )
        except Exception as e:
            logger.error("Failed to notify admin %s: %s", admin_id, e)
