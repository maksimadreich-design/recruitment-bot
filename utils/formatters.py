import html
from typing import Dict, Any, List, Optional
from database.models import Candidate, AIRecommendation, OwnerDecision
from questions.questions_data import QUESTIONS
from scoring.compensation import calculate_total_earnings, get_commission_percentage_str

def format_admin_candidate_card(candidate: Candidate) -> str:
    """Format full structured candidate notification card for admin in HTML."""
    name_display = html.escape(candidate.name or "Не вказано")
    username_display = f"@{html.escape(candidate.username)}" if candidate.username else "без username"
    phone_display = html.escape(candidate.phone or "Не вказано")

    gen_score = candidate.score or 0
    sales_score = candidate.sales_potential_score or gen_score
    
    # AI Recommendation Badge
    ai_rec = candidate.ai_recommendation or AIRecommendation.POTENTIAL
    if ai_rec == AIRecommendation.STRONG:
        ai_rec_badge = "🔥 STRONG"
    elif ai_rec == AIRecommendation.POTENTIAL:
        ai_rec_badge = "🟢 POTENTIAL"
    elif ai_rec == AIRecommendation.WEAK:
        ai_rec_badge = "🟡 WEAK"
    else:
        ai_rec_badge = "🔴 REJECT_RECOMMENDED"

    # Owner Decision Badge
    owner_dec = candidate.owner_decision or OwnerDecision.PENDING
    if owner_dec == OwnerDecision.PENDING:
        owner_dec_display = "⏳ Очікує рішення"
    elif owner_dec == OwnerDecision.INTERVIEW:
        owner_dec_display = f"✅ INTERVIEW ({candidate.decision_timestamp or 'прийнято'})"
    elif owner_dec == OwnerDecision.TEST:
        owner_dec_display = f"🟡 TEST ({candidate.decision_timestamp or 'прийнято'})"
    elif owner_dec == OwnerDecision.REJECTED:
        owner_dec_display = f"❌ REJECTED ({candidate.decision_timestamp or 'прийнято'})"
    elif owner_dec == OwnerDecision.RESERVE:
        owner_dec_display = f"📌 RESERVE ({candidate.decision_timestamp or 'прийнято'})"
    elif owner_dec == OwnerDecision.HIRED:
        owner_dec_display = f"🏆 HIRED ({candidate.decision_timestamp or 'прийнято'})"
    else:
        owner_dec_display = html.escape(owner_dec)

    # Terms acceptance
    if candidate.terms_accepted:
        terms_display = f"✅ Погодився (Дата: {candidate.terms_accepted_at or 'підтверджено'})"
    else:
        terms_display = "⚠️ Не підтверджено"

    # Strengths & Weaknesses
    strengths = candidate.strengths or []
    weaknesses = candidate.weaknesses or []
    str_list = "\n".join([f"• {html.escape(s)}" for s in strengths[:3]]) if strengths else "• Не виявлено"
    risk_list = "\n".join([f"• {html.escape(w)}" for w in weaknesses[:3]]) if weaknesses else "• Не виявлено"

    # Red Flags
    red_flags = candidate.red_flags or []
    if red_flags:
        rf_lines = []
        for rf in red_flags:
            flag_txt = html.escape(rf.get("flag", str(rf)))
            sev = rf.get("severity", "MEDIUM")
            sev_badge = "🔴 HIGH" if sev == "HIGH" else ("🟠 MEDIUM" if sev == "MEDIUM" else "🟡 LOW")
            rf_lines.append(f"• [{sev_badge}] {flag_txt}")
        red_flags_str = "\n".join(rf_lines)
    else:
        red_flags_str = "• Червоних прапорців не виявлено"

    # Positive Signals
    pos_signals = candidate.positive_signals or []
    pos_str = "\n".join([f"• {html.escape(ps)}" for ps in pos_signals[:4]]) if pos_signals else "• Базова відповідність"

    ai_summary = html.escape(candidate.ai_recommendation_reason or candidate.psychological_profile or "Кандидат пройшов скринінг.")

    # All 10 Answers
    answers_blocks = []
    answers_dict = candidate.answers or {}
    for q in QUESTIONS:
        q_ans = answers_dict.get(f"Q{q.id}", answers_dict.get(str(q.id), "—"))
        answers_blocks.append(
            f"<b>{q.id}. {html.escape(q.title)}:</b>\n"
            f"<i>«{html.escape(str(q_ans))}»</i>"
        )
    answers_str = "\n\n".join(answers_blocks)

    voice_status = "✅ Аудіо надіслано нижче" if candidate.voice_file_id else "❌ Не надано"

    card = (
        f"🔥 <b>НОВИЙ КАНДИДАТ #{candidate.candidate_id}</b>\n\n"
        f"👤 <b>Ім'я:</b> {name_display}\n"
        f"📱 <b>Telegram:</b> {username_display} (ID: <code>{candidate.telegram_id}</code>)\n"
        f"📞 <b>Телефон:</b> {phone_display}\n"
        f"📋 <b>Умови роботи:</b> {terms_display}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 <b>AI ASSESSMENT</b>\n\n"
        f"<b>General Score:</b>\n{gen_score}/100\n\n"
        f"<b>Sales Potential:</b>\n{sales_score}/100\n\n"
        f"<b>AI Recommendation:</b>\n{ai_rec_badge}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"💪 <b>Сильні сторони:</b>\n{str_list}\n\n"
        f"⚠️ <b>Слабкі сторони:</b>\n{risk_list}\n\n"
        f"🚩 <b>Red Flags:</b>\n{red_flags_str}\n\n"
        f"🟢 <b>Positive Signals:</b>\n{pos_str}\n\n"
        f"🧠 <b>AI Summary:</b>\n<i>«{ai_summary}»</i>\n\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"🎯 <b>OWNER DECISION:</b>\n<b>{owner_dec_display}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"📝 <b>ВІДПОВІДІ КАНДИДАТА:</b>\n\n"
        f"{answers_str}\n\n"
        f"🎤 <b>Голосовий тест:</b> {voice_status}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🕐 <b>Створено:</b> {candidate.created_at or 'Тільки що'}"
    )
    return card

# Backward compatibility alias
format_admin_candidate_report = format_admin_candidate_card

def format_manager_activity_card(candidate: Candidate) -> str:
    """Format manager activity, commission tier, and earnings breakdown."""
    name = html.escape(candidate.name or "Менеджер")
    contacts = candidate.activity_contacts_current_week or 0
    contacts_done_badge = "✅ (Норму виконано)" if contacts >= 40 else f"({40 - contacts} до норми)"
    
    bonus_active = candidate.activity_bonus_active
    bonus_status = "🟢 АКТИВНИЙ" if bonus_active else "⚪ НЕ АКТИВНИЙ"
    bonus_until = f" (Діє до: {candidate.activity_bonus_active_until})" if candidate.activity_bonus_active_until and bonus_active else ""

    sales_count = candidate.sales_current_month or 0
    sales_rev = candidate.sales_revenue_current_month or 0.0
    comm_pct = get_commission_percentage_str(sales_count)

    earnings = calculate_total_earnings(
        total_sales_revenue=sales_rev,
        closed_clients_count=sales_count,
        clients_closed_in_bonus_week=sales_count if bonus_active else 0,
        is_activity_bonus_active=bonus_active
    )

    return (
        f"💼 <b>ПРОФІЛЬ ТА ДОХІД МЕНЕДЖЕРА #{candidate.candidate_id}</b>\n"
        f"👤 <b>{name}</b> (@{html.escape(candidate.username or '-')})\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📞 <b>Підтверджені контакти цього тижня:</b>\n"
        f"<b>{contacts} / 40</b> {contacts_done_badge}\n\n"
        f"🔥 <b>Бонус за активність (+1000 грн/клієнт):</b>\n"
        f"<b>{bonus_status}</b>{bonus_until}\n\n"
        f"📊 <b>Закритих клієнтів цього місяця:</b> <b>{sales_count}</b>\n"
        f"💰 <b>Загальна каса продажів:</b> <b>{sales_rev:,.2f} грн</b>\n"
        f"📈 <b>Поточна ставка комісії:</b> <b>{comm_pct}</b> <i>(на всі продажі місяця)</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💵 <b>Комісія з продажів:</b> {earnings['commission_amount']:,.2f} грн\n"
        f"🎁 <b>Activity Bonus:</b> +{earnings['activity_bonus_amount']:,.2f} грн\n"
        f"🏆 <b>РАЗОМ ДО ВИПЛАТИ:</b> <b>{earnings['total_earnings']:,.2f} грн</b>"
    )

def format_ai_explanation_view(candidate: Candidate) -> str:
    """Format AI Explanation breakdown for admin."""
    expl = candidate.ai_explanation or {}
    drivers = html.escape(expl.get("score_drivers", "Зрілість відповідей на ключові питання."))
    strongest = html.escape(expl.get("strongest_answers", "Питання 8 та питання по запереченнях."))
    risks = html.escape(expl.get("risks", "Потребує перевірки на живому дзвінку."))
    live_check = html.escape(expl.get("live_check", "Провести рольову гру з холодним дзвінком."))

    return (
        f"🧠 <b>ПОЯСНЕННЯ AI ОЦІНКИ КАНДИДАТА #{candidate.candidate_id}</b>\n"
        f"👤 {html.escape(candidate.name or 'Кандидат')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📈 <b>Що найбільше вплинуло на бал:</b>\n{drivers}\n\n"
        f"🌟 <b>Найсильніші відповіді:</b>\n{strongest}\n\n"
        f"⚠️ <b>Ключові ризики:</b>\n{risks}\n\n"
        f"🎯 <b>Що перевірити на живій співбесіді:</b>\n{live_check}"
    )

def format_interview_questions_view(candidate: Candidate) -> str:
    """Format 5 custom tailored interview questions."""
    name = html.escape(candidate.name or "Кандидат")
    questions = candidate.interview_questions or []
    if not questions:
        questions = [
            "Уяви, що власник каже: «У нас і так достатньо клієнтів». Які 2 зустрічні питання ти поставиш?",
            "Як ти обходиш секретаря, якщо керівника ніколи «немає на місці»?",
            "Поясни простими словами власнику бізнесу, як автоматизація принесе йому гроші.",
            "Як ти дієш після 20 поспіль відмов у першій половині дня?",
            "Розкажи про свій реальний приклад закриття складної угоди."
        ]

    q_lines = [f"<b>{i+1}.</b> {html.escape(q)}" for i, q in enumerate(questions[:5])]
    q_str = "\n\n".join(q_lines)

    return (
        f"📋 <b>5 ТАРГЕТНИХ ПИТАНЬ ДЛЯ СПІВБЕСІДИ З #{candidate.candidate_id}</b>\n"
        f"👤 {name}\n"
        f"<i>(Сформовано AI на основі зон росту кандидата)</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{q_str}\n\n"
        f"💡 <i>Порада: перевірте в першу чергу здатність кандидата слухати та ставити зустрічні відкриті запитання.</i>"
    )

def format_answers_view(candidate: Candidate) -> str:
    """Format full list of all 10 candidate answers."""
    name = html.escape(candidate.name or "Кандидат")
    answers_dict = candidate.answers or {}
    blocks = []
    for q in QUESTIONS:
        q_ans = answers_dict.get(f"Q{q.id}", answers_dict.get(str(q.id), "—"))
        blocks.append(
            f"<b>{q.id}. {html.escape(q.title)}:</b>\n"
            f"<i>«{html.escape(str(q_ans))}»</i>"
        )
    answers_str = "\n\n".join(blocks)

    return (
        f"📝 <b>ПОВНІ ВІДПОВІДІ КАНДИДАТА #{candidate.candidate_id}</b>\n"
        f"👤 {name}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{answers_str}"
    )

def format_candidate_comparison(c1: Candidate, c2: Candidate) -> str:
    """Format side-by-side comparison of 2 candidates."""
    return (
        f"⚖️ <b>ПОРІВНЯННЯ КАНДИДАТІВ #{c1.candidate_id} vs #{c2.candidate_id}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Кандидат 1:</b> {html.escape(c1.name or 'N/A')} (@{html.escape(c1.username or '-')})\n"
        f"  • General Score: <b>{c1.score or 0}/100</b>\n"
        f"  • Sales Potential: <b>{c1.sales_potential_score or 0}/100 ({c1.sales_potential_level or '-'})</b>\n"
        f"  • AI Recommendation: <b>{c1.ai_recommendation}</b>\n"
        f"  • Owner Decision: <b>{c1.owner_decision}</b>\n\n"
        f"👤 <b>Кандидат 2:</b> {html.escape(c2.name or 'N/A')} (@{html.escape(c2.username or '-')})\n"
        f"  • General Score: <b>{c2.score or 0}/100</b>\n"
        f"  • Sales Potential: <b>{c2.sales_potential_score or 0}/100 ({c2.sales_potential_level or '-'})</b>\n"
        f"  • AI Recommendation: <b>{c2.ai_recommendation}</b>\n"
        f"  • Owner Decision: <b>{c2.owner_decision}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏆 <b>Лідер за Sales Potential:</b> <b>{'Кандидат 1' if (c1.sales_potential_score or 0) >= (c2.sales_potential_score or 0) else 'Кандидат 2'}</b>"
    )

def format_stats_message(stats: Dict[str, Any]) -> str:
    """Format stats with strict separation of AI Assessment and Owner Decisions."""
    ai_s = stats.get("ai", {})
    ow_s = stats.get("owner", {})

    return (
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>AI ASSESSMENT</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Total: <b>{ai_s.get('total', 0)}</b>\n"
        f"🔥 Strong: <b>{ai_s.get('strong', 0)}</b>\n"
        f"🟢 Potential: <b>{ai_s.get('potential', 0)}</b>\n"
        f"🟡 Weak: <b>{ai_s.get('weak', 0)}</b>\n"
        f"🔴 Reject Recommended: <b>{ai_s.get('reject_recommended', 0)}</b>\n\n"
        f"🎯 Середній General Score: <b>{ai_s.get('avg_score', 0)}/100</b>\n"
        f"🔥 Середній Sales Potential: <b>{ai_s.get('avg_sales_score', 0)}/100</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🎯 <b>OWNER DECISIONS</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"⏳ Pending (Очікує): <b>{ow_s.get('pending', 0)}</b>\n"
        f"✅ Interview: <b>{ow_s.get('interview', 0)}</b>\n"
        f"🟡 Test: <b>{ow_s.get('test', 0)}</b>\n"
        f"❌ Rejected: <b>{ow_s.get('rejected', 0)}</b>\n"
        f"📌 Reserve: <b>{ow_s.get('reserve', 0)}</b>\n"
        f"🏆 Hired: <b>{ow_s.get('hired', 0)}</b>"
    )
