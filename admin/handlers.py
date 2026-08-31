import logging
import html
from typing import Optional, List
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, Filter

from config import config
from database.db import db
from database.models import Candidate, AIRecommendation, OwnerDecision
from utils.keyboards import get_admin_candidate_keyboard
from utils.formatters import (
    format_admin_candidate_card,
    format_ai_explanation_view,
    format_interview_questions_view,
    format_answers_view,
    format_candidate_comparison,
    format_stats_message
)

logger = logging.getLogger(__name__)
admin_router = Router()

class IsAdmin(Filter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user_id = event.from_user.id
        if not config.ADMIN_IDS:
            return True
        return user_id in config.ADMIN_IDS

admin_router.message.filter(IsAdmin())
admin_router.callback_query.filter(IsAdmin())

@admin_router.message(Command("manager"))
async def cmd_view_manager(message: Message):
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Вкажіть ID менеджера: <code>/manager 1</code>", parse_mode="HTML")
        return

    candidate_id = int(parts[1])
    candidate = await db.get_candidate_by_id(candidate_id)
    if not candidate:
        await message.answer("Менеджера не знайдено.")
        return

    card_text = format_manager_activity_card(candidate)
    await message.answer(card_text, parse_mode="HTML")

@admin_router.message(Command("add_contacts"))
async def cmd_add_contacts(message: Message):
    parts = message.text.split()
    if len(parts) < 3 or not parts[1].isdigit() or not parts[2].isdigit():
        await message.answer("Формат: <code>/add_contacts [ID] [кількість]</code>\nПриклад: <code>/add_contacts 1 10</code>", parse_mode="HTML")
        return

    candidate_id = int(parts[1])
    count = int(parts[2])
    cand = await db.record_manager_activity_contacts(candidate_id, count)
    if cand:
        await message.answer(f"✅ Додано <b>{count}</b> контактів для менеджера #{candidate_id}. Всього цього тижня: <b>{cand.activity_contacts_current_week}/40</b>.", parse_mode="HTML")
    else:
        await message.answer("Менеджера не знайдено.")

@admin_router.message(Command("add_sale"))
async def cmd_add_sale(message: Message):
    parts = message.text.split()
    if len(parts) < 3 or not parts[1].isdigit():
        await message.answer("Формат: <code>/add_sale [ID] [сума_грн]</code>\nПриклад: <code>/add_sale 1 20000</code>", parse_mode="HTML")
        return

    candidate_id = int(parts[1])
    try:
        amount = float(parts[2])
    except ValueError:
        await message.answer("Некоректна сума.")
        return

    cand = await db.record_manager_sale(candidate_id, amount)
    if cand:
        card = format_manager_activity_card(cand)
        await message.answer(f"🎉 Продаж на <b>{amount:,.2f} грн</b> зафіксовано!\n\n{card}", parse_mode="HTML")
    else:
        await message.answer("Менеджера не знайдено.")

@admin_router.message(Command("close_week"))
async def cmd_close_week(message: Message):
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Формат: <code>/close_week [ID]</code>", parse_mode="HTML")
        return

    candidate_id = int(parts[1])
    cand = await db.evaluate_and_close_weekly_activity(candidate_id)
    if cand:
        status_text = "🟢 АКТИВОВАНО (+1000 грн за клієнта)" if cand.activity_bonus_active else "⚪ НЕ АКТИВОВАНО (<40 контактів)"
        await message.answer(f"📅 Робочий тиждень закрито.\nПідсумок контактів: <b>{cand.activity_contacts_last_week}/40</b>\nБонус наступного тижня: <b>{status_text}</b>", parse_mode="HTML")
    else:
        await message.answer("Менеджера не знайдено.")

@admin_router.message(Command("stats"))
async def cmd_stats(message: Message):
    stats = await db.get_stats()
    text = format_stats_message(stats)
    await message.answer(text, parse_mode="HTML")

@admin_router.message(Command("top"))
async def cmd_top_candidates(message: Message):
    top_cands = await db.get_top_candidates(limit=10)
    if not top_cands:
        await message.answer("Список кандидатів порожній.")
        return

    lines = [
        "🏆 <b>ТОП-10 КАНДИДАТІВ ЗА SALES POTENTIAL</b>",
        "━━━━━━━━━━━━━━━━━━━━━━━━"
    ]
    for idx, c in enumerate(top_cands):
        name = html.escape(c.name or "Кандидат")
        uname = f"@{html.escape(c.username)}" if c.username else "-"
        gen_s = c.score or 0
        sales_s = c.sales_potential_score or 0
        lines.append(
            f"<b>{idx+1}. #{c.candidate_id}</b> {name} ({uname})\n"
            f"   └ 📊 Score: <b>{gen_s}</b> | 🔥 Sales: <b>{sales_s}</b> | AI: <b>{c.ai_recommendation}</b>\n"
            f"   └ 🎯 Рішення власника: <code>{c.owner_decision}</code> | Деталі: /view_{c.candidate_id}"
        )
    await message.answer("\n\n".join(lines), parse_mode="HTML")

@admin_router.message(Command("compare"))
async def cmd_compare_candidates(message: Message):
    parts = message.text.split()
    if len(parts) < 3 or not parts[1].isdigit() or not parts[2].isdigit():
        await message.answer(
            "Вкажіть два ID кандидатів для порівняння: <code>/compare 1 2</code>",
            parse_mode="HTML"
        )
        return

    id1, id2 = int(parts[1]), int(parts[2])
    c1, c2 = await db.compare_candidates(id1, id2)
    if not c1 or not c2:
        await message.answer("Одного або обох кандидатів не знайдено в базі.")
        return

    comp_text = format_candidate_comparison(c1, c2)
    await message.answer(comp_text, parse_mode="HTML")

@admin_router.message(Command("candidates"))
@admin_router.message(Command("admin"))
async def cmd_candidates(message: Message):
    """Shows all candidates without hiding anyone."""
    candidates = await db.list_all_candidates(limit=30)
    await send_candidate_list(message, candidates, "👥 ВСІ КАНДИДАТИ В БАЗІ")

# --- AI Recommendation Filters ---

@admin_router.message(Command("strong"))
async def cmd_filter_strong(message: Message):
    candidates = await db.list_by_ai_recommendation(AIRecommendation.STRONG, limit=30)
    await send_candidate_list(message, candidates, "🔥 AI RECOMMENDATION = STRONG")

@admin_router.message(Command("potential"))
async def cmd_filter_potential(message: Message):
    candidates = await db.list_by_ai_recommendation(AIRecommendation.POTENTIAL, limit=30)
    await send_candidate_list(message, candidates, "🟢 AI RECOMMENDATION = POTENTIAL")

@admin_router.message(Command("weak"))
async def cmd_filter_weak(message: Message):
    candidates = await db.list_by_ai_recommendation(AIRecommendation.WEAK, limit=30)
    await send_candidate_list(message, candidates, "🟡 AI RECOMMENDATION = WEAK")

@admin_router.message(Command("rejected"))
@admin_router.message(Command("reject_recommended"))
async def cmd_filter_reject_recommended(message: Message):
    candidates = await db.list_by_ai_recommendation(AIRecommendation.REJECT_RECOMMENDED, limit=30)
    await send_candidate_list(message, candidates, "🔴 AI RECOMMENDATION = REJECT_RECOMMENDED")

# --- Owner Decision Filters ---

@admin_router.message(Command("pending"))
async def cmd_filter_pending(message: Message):
    candidates = await db.list_by_owner_decision(OwnerDecision.PENDING, limit=30)
    await send_candidate_list(message, candidates, "⏳ OWNER DECISION = PENDING (Очікують)")

@admin_router.message(Command("interview"))
async def cmd_filter_interview(message: Message):
    candidates = await db.list_by_owner_decision(OwnerDecision.INTERVIEW, limit=30)
    await send_candidate_list(message, candidates, "✅ OWNER DECISION = INTERVIEW")

@admin_router.message(Command("test"))
async def cmd_filter_test(message: Message):
    candidates = await db.list_by_owner_decision(OwnerDecision.TEST, limit=30)
    await send_candidate_list(message, candidates, "🟡 OWNER DECISION = TEST")

@admin_router.message(Command("owner_rejected"))
async def cmd_filter_owner_rejected(message: Message):
    candidates = await db.list_by_owner_decision(OwnerDecision.REJECTED, limit=30)
    await send_candidate_list(message, candidates, "❌ OWNER DECISION = REJECTED")

@admin_router.message(Command("reserve"))
async def cmd_filter_reserve(message: Message):
    candidates = await db.list_by_owner_decision(OwnerDecision.RESERVE, limit=30)
    await send_candidate_list(message, candidates, "📌 OWNER DECISION = RESERVE")

@admin_router.message(Command("hired"))
async def cmd_filter_hired(message: Message):
    candidates = await db.list_by_owner_decision(OwnerDecision.HIRED, limit=30)
    await send_candidate_list(message, candidates, "🏆 OWNER DECISION = HIRED")

@admin_router.message(Command("view"))
async def cmd_view_candidate(message: Message):
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Вкажіть ID кандидата: <code>/view 1</code>", parse_mode="HTML")
        return

    candidate_id = int(parts[1])
    candidate = await db.get_candidate_by_id(candidate_id)
    if not candidate:
        await message.answer("Кандидата з таким ID не знайдено.")
        return

    card_text = format_admin_candidate_card(candidate)
    admin_kb = get_admin_candidate_keyboard(candidate.candidate_id, candidate.owner_decision)
    await message.answer(card_text, reply_markup=admin_kb, parse_mode="HTML")

@admin_router.message(F.text.regexp(r"^/view_(\d+)$"))
async def cmd_view_candidate_shortcut(message: Message):
    parts = message.text.split("_")
    if len(parts) == 2 and parts[1].isdigit():
        candidate_id = int(parts[1])
        candidate = await db.get_candidate_by_id(candidate_id)
        if candidate:
            card_text = format_admin_candidate_card(candidate)
            admin_kb = get_admin_candidate_keyboard(candidate.candidate_id, candidate.owner_decision)
            await message.answer(card_text, reply_markup=admin_kb, parse_mode="HTML")
        else:
            await message.answer("Кандидата не знайдено.")

@admin_router.message(Command("reset"))
async def cmd_reset_candidate(message: Message):
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Вкажіть Telegram ID кандидата для скидання: <code>/reset 123456789</code>", parse_mode="HTML")
        return

    tg_id = int(parts[1])
    success = await db.reset_candidate(tg_id)
    if success:
        await message.answer(f"✅ Кандидата з Telegram ID <code>{tg_id}</code> успішно видалено/скинуто.", parse_mode="HTML")
    else:
        await message.answer(f"⚠️ Кандидата з Telegram ID {tg_id} не знайдено в базі.")

@admin_router.callback_query(F.data.startswith("adm_decide:"))
@admin_router.callback_query(F.data.startswith("adm_status:"))
async def cb_admin_decide(callback: CallbackQuery):
    """Updates OWNER_DECISION. AI recommendation remains untouched."""
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Некоректний запит", show_alert=True)
        return

    candidate_id = int(parts[1])
    decision = parts[2]
    admin_id = callback.from_user.id

    success = await db.set_owner_decision(candidate_id, decision, admin_id=admin_id)
    if success:
        cand = await db.get_candidate_by_id(candidate_id)
        await callback.answer(f"Рішення власника встановлено: {decision}", show_alert=False)
        updated_kb = get_admin_candidate_keyboard(candidate_id, decision)
        
        # Update text or markup
        try:
            updated_card_text = format_admin_candidate_card(cand)
            if len(updated_card_text) <= 4000:
                await callback.message.edit_text(updated_card_text, reply_markup=updated_kb, parse_mode="HTML")
            else:
                await callback.message.edit_reply_markup(reply_markup=updated_kb)
        except Exception as e:
            logger.debug("Edit message note: %s", e)
            try:
                await callback.message.edit_reply_markup(reply_markup=updated_kb)
            except Exception:
                pass
    else:
        await callback.answer("Помилка збереження рішення", show_alert=True)

@admin_router.callback_query(F.data.startswith("adm_explain:"))
async def cb_admin_explain(callback: CallbackQuery):
    candidate_id = int(callback.data.split(":")[1])
    candidate = await db.get_candidate_by_id(candidate_id)
    if not candidate:
        await callback.answer("Кандидата не знайдено", show_alert=True)
        return

    await callback.answer()
    text = format_ai_explanation_view(candidate)
    await callback.message.answer(text, parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("adm_questions:"))
async def cb_admin_questions(callback: CallbackQuery):
    candidate_id = int(callback.data.split(":")[1])
    candidate = await db.get_candidate_by_id(candidate_id)
    if not candidate:
        await callback.answer("Кандидата не знайдено", show_alert=True)
        return

    await callback.answer()
    text = format_interview_questions_view(candidate)
    await callback.message.answer(text, parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("adm_answers:"))
async def cb_admin_answers(callback: CallbackQuery):
    candidate_id = int(callback.data.split(":")[1])
    candidate = await db.get_candidate_by_id(candidate_id)
    if not candidate:
        await callback.answer("Кандидата не знайдено", show_alert=True)
        return

    await callback.answer()
    text = format_answers_view(candidate)
    if len(text) <= 4000:
        await callback.message.answer(text, parse_mode="HTML")
    else:
        for chunk in [text[i:i+3800] for i in range(0, len(text), 3800)]:
            await callback.message.answer(chunk, parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("adm_reset:"))
async def cb_admin_reset(callback: CallbackQuery):
    parts = callback.data.split(":")
    if len(parts) != 2:
        await callback.answer("Некоректний запит", show_alert=True)
        return

    candidate_id = int(parts[1])
    cand = await db.get_candidate_by_id(candidate_id)
    if cand:
        await db.reset_candidate(cand.telegram_id)
        await callback.answer("Кандидата скинуто. Він може пройти відбір заново.", show_alert=True)
        await callback.message.edit_reply_markup(reply_markup=None)
    else:
        await callback.answer("Кандидата не знайдено", show_alert=True)

async def send_candidate_list(message: Message, candidates: List[Candidate], title: str):
    if not candidates:
        await message.answer(f"<b>{title}</b>\n\nСписок порожній.", parse_mode="HTML")
        return

    lines = [f"<b>{title}</b>\n━━━━━━━━━━━━━━━━━━━━━━━━"]
    for c in candidates:
        name = html.escape(c.name or "Анонім")
        uname = f"@{html.escape(c.username)}" if c.username else "без юзернейму"
        gen_s = c.score or 0
        sales_s = c.sales_potential_score or gen_s
        lines.append(
            f"• <b>#{c.candidate_id}</b> {name} ({uname})\n"
            f"   └ Score: <b>{gen_s}</b> | Sales: <b>{sales_s}</b> | AI: <b>{c.ai_recommendation}</b>\n"
            f"   └ Рішення: <code>{c.owner_decision}</code> | Деталі: /view_{c.candidate_id}"
        )
    text = "\n\n".join(lines)
    await message.answer(text, parse_mode="HTML")
