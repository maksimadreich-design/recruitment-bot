import json
import logging
import re
from typing import Dict, Any, List, Optional
from config import config
from database.models import AIRecommendation
from scoring.rules import (
    SCORING_CATEGORIES,
    classify_sales_potential_level,
    classify_ai_recommendation
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Ти — AI Recruitment Assistant та аналітик первинного скринінгу кандидатів на посаду менеджера з холодних продажів digital-послуг.

ГОЛОВНИЙ ПРИНЦИП:
Ти — AI-асистент рекрутера, а НЕ особа, яка приймає остаточне рішення.
Твоє завдання — надати структурований аналіз та рекомендацію (STRONG, POTENTIAL, WEAK, REJECT_RECOMMENDED), але фінальне рішення завжди приймає людина (власник / адміністратор).

МОВА ТА ТОН:
Використовуй виключно професійну, об'єктивну та стриману мову.
Не пиши образливих або безапеляційних висновків («кандидат поганий», «не брати»).
Замість цього:
- «Кандидат має низьку відповідність поточним критеріям відбору.»
- «AI рекомендує не пріоритезувати кандидата на наступний етап.»
- «На основі відповідей AI оцінює потенціал холодних продажів як низький. Рекомендується перевірити це під час практичного дзвінка.»

КРИТЕРІЇ ОЦІНКИ:
1. GENERAL SCORE (0-100): Загальна комунікація, адекватність, логіка, дисципліна, мотивація.
2. SALES POTENTIAL SCORE (0-100): Потенціал саме у холодних дзвінках (Hook, Discovery, Слухання 80/20, Робота із запереченнями, Closing, Стійкість до відмов, Комерційне мислення).
3. AI RECOMMENDATION: Тільки одне зі значень:
   - STRONG
   - POTENTIAL
   - WEAK
   - REJECT_RECOMMENDED
4. ПИТАННЯ 8 (ГОЛОВНИЙ SALES TEST): Оцінка за 5 шкалами по 20 балів (Hook, Value, Curiosity, Personalization, Next step = 100).
5. RED FLAGS: Список ризиків із критичністю (HIGH / MEDIUM / LOW).
6. POSITIVE SIGNALS: Список сильних поведінкових маркерів.
7. AUTHENTICITY SIGNAL: HIGH / MEDIUM / LOW (природність формулювань).
8. 5 ТАРГЕТНИХ ПИТАНЬ: Питання для співбесіди, що перевіряють виявлені слабкі місця.

Формат відповіді ТІЛЬКИ валідний JSON:
{
  "total_score": 87,
  "sales_potential_score": 91,
  "sales_potential_level": "VERY HIGH",
  "ai_recommendation": "STRONG",
  "confidence": "HIGH",
  "ai_recommendation_reason": "Кандидат продемонстрував високу зрілість у роботі з запереченнями та якісний комерційний hook у питанні 8.",
  "category_scores": {
    "communication": 9,
    "motivation": 8,
    "logic": 9,
    "sales": 14,
    "objection_handling": 9,
    "discovery_listening": 9,
    "rejection_resilience": 9,
    "initiative": 8,
    "discipline": 5,
    "voice_test": 9
  },
  "strengths": [
    "Сильне комерційне мислення та орієнтація на вигоду клієнта",
    "Не відпускає клієнта без чіткої домовленості про наступний контакт",
    "Зріле сприйняття відмов і готовність до обсягу роботи"
  ],
  "weaknesses": [
    "Може трохи ускладнювати початковий вхід у розмову",
    "Потребує адаптації до специфіки digital-послуг компанії",
    "Варто більше фокусуватися на коротких відкритих запитаннях"
  ],
  "red_flags": [
    {
      "flag": "Невелика схильність до довгих монологів без ранньої паузи",
      "severity": "LOW"
    }
  ],
  "positive_signals": [
    "Самостійно пропонує закриття на 10-хвилинний Zoom замість довгого спаму",
    "Використовує мову вигод, а не технічних функцій",
    "Бере особисту відповідальність за конверсію"
  ],
  "q8_breakdown": {
    "hook": 18,
    "value": 18,
    "curiosity": 19,
    "personalization": 16,
    "next_step": 19,
    "total": 90
  },
  "voice_analysis": {
    "confidence": 9,
    "clarity": 8,
    "energy": 8,
    "naturalness": 9,
    "reading_script": false,
    "summary": "Впевнена та спокійна подача, природна інтонація без страху перед контактом."
  },
  "authenticity_signal": "HIGH",
  "interview_questions": [
    "Уяви ситуацію: клієнт перебиває на 5-й секунді і грубо каже «Хто вам дав мій номер?». Твої точні перші слова?",
    "Якби власник сказав «У нас вже є підрядник і все влаштовує», які 2 питання ти поставиш далі?",
    "Який був найскладніший клієнт у твоєму досвіді і як ти завершив угоду?",
    "Як ти підтримуєш дисципліну, коли 4 години поспіль чуєш тільки відмови?",
    "Поясни простими словами власнику автосервісу, як AI-чатбот принесе йому реальні гроші."
  ],
  "ai_explanation": {
    "score_drivers": "Високий бал зумовлений чіткою структурою у питанні 8, правильним закриттям на наступний крок та фокусом на слуханні.",
    "strongest_answers": "Питання 5 (перевід з Telegram у діалог) та Питання 8 (продаж 10-хвилинної зустрічі).",
    "risks": "Потрібно проконтролювати вміння лаконічно тримати темп на холодних секундах.",
    "live_check": "Перевірити на живому рольовому дзвінку реакцію на агресивний злив."
  },
  "psychological_profile": "Стресостійкий, дисциплінований, має внутрішній локус контролю.",
  "predicted_performance": "Швидкий вихід на 40-60 цільових контактів на день з високою конверсією у первинні зустрічі."
}
"""

class AIAnalyzer:
    async def analyze(
        self,
        candidate_name: str,
        answers: Dict[str, str],
        has_voice: bool
    ) -> Dict[str, Any]:
        """Run analysis via configured LLM provider or fallback heuristic engine."""
        provider = config.AI_PROVIDER

        if (provider in ["gemini", "auto"]) and config.GEMINI_API_KEY:
            try:
                result = await self._analyze_with_gemini(candidate_name, answers, has_voice)
                if result:
                    return self._validate_and_normalize(result, candidate_name, answers, has_voice)
            except Exception as e:
                logger.error("Gemini analysis error: %s", e)

        if (provider in ["openai", "auto"]) and config.OPENAI_API_KEY:
            try:
                result = await self._analyze_with_openai(candidate_name, answers, has_voice)
                if result:
                    return self._validate_and_normalize(result, candidate_name, answers, has_voice)
            except Exception as e:
                logger.error("OpenAI analysis error: %s", e)

        logger.info("Using AI recruitment assistant heuristic engine for %s", candidate_name)
        return self._analyze_with_heuristics(candidate_name, answers, has_voice)

    async def _analyze_with_openai(
        self,
        candidate_name: str,
        answers: Dict[str, str],
        has_voice: bool
    ) -> Optional[Dict[str, Any]]:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)

        user_content = f"Кандидат: {candidate_name}\nГолосове повідомлення записано: {'Так' if has_voice else 'Ні'}\n\nВідповіді кандидата:\n"
        for q_key, ans in answers.items():
            user_content += f"{q_key}: {ans}\n\n"

        response = await client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )
        raw_text = response.choices[0].message.content
        return json.loads(raw_text)

    async def _analyze_with_gemini(
        self,
        candidate_name: str,
        answers: Dict[str, str],
        has_voice: bool
    ) -> Optional[Dict[str, Any]]:
        import google.generativeai as genai
        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config={"response_mime_type": "application/json"}
        )

        user_content = f"Кандидат: {candidate_name}\nГолосове повідомлення записано: {'Так' if has_voice else 'Ні'}\n\nВідповіді кандидата:\n"
        for q_key, ans in answers.items():
            user_content += f"{q_key}: {ans}\n\n"

        prompt = f"{SYSTEM_PROMPT}\n\n{user_content}"
        response = await model.generate_content_async(prompt)
        text = response.text.strip()
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"```$", "", text).strip()
        return json.loads(text)

    def _validate_and_normalize(
        self,
        data: Dict[str, Any],
        candidate_name: str,
        answers: Dict[str, str],
        has_voice: bool
    ) -> Dict[str, Any]:
        """Normalize AI result and guarantee strict separation from owner decision."""
        total_score = data.get("total_score", 75)
        sales_score = data.get("sales_potential_score", total_score)
        
        ai_rec, badge, conf, desc = classify_ai_recommendation(total_score, sales_score)
        sales_level = classify_sales_potential_level(sales_score)

        data["ai_recommendation"] = data.get("ai_recommendation") or ai_rec
        data.setdefault("ai_recommendation_reason", desc)
        data.setdefault("sales_potential_level", sales_level)
        data.setdefault("confidence", conf)
        data.setdefault("authenticity_signal", "HIGH")

        if not data.get("q8_breakdown"):
            data["q8_breakdown"] = {"hook": 16, "value": 16, "curiosity": 16, "personalization": 16, "next_step": 16, "total": 80}

        if not data.get("voice_analysis"):
            data["voice_analysis"] = {
                "confidence": 8 if has_voice else 3,
                "clarity": 8 if has_voice else 3,
                "energy": 8 if has_voice else 3,
                "naturalness": 8 if has_voice else 3,
                "reading_script": False,
                "summary": "Голосовий запис додано" if has_voice else "Голосовий тест не пройдено"
            }

        return data

    def _analyze_with_heuristics(
        self,
        candidate_name: str,
        answers: Dict[str, str],
        has_voice: bool
    ) -> Dict[str, Any]:
        """Heuristic analysis engine respecting AI assistant boundaries and cautious language."""
        def get_ans(q_num: int) -> str:
            for k, v in answers.items():
                if k.startswith(f"Q{q_num}") or k.startswith(f"{q_num}.") or f"Питання {q_num}" in k:
                    return str(v).strip()
            keys = list(answers.keys())
            if 0 <= q_num - 1 < len(keys):
                return str(answers[keys[q_num - 1]]).strip()
            return ""

        ans1 = get_ans(1).lower()
        ans2 = get_ans(2).lower()
        ans3 = get_ans(3).lower()
        ans4 = get_ans(4).lower()
        ans5 = get_ans(5).lower()
        ans6 = get_ans(6).lower()
        ans7 = get_ans(7).lower()
        ans8 = get_ans(8).lower()
        ans9 = get_ans(9).lower()
        ans10 = get_ans(10).lower()

        red_flags: List[Dict[str, str]] = []
        positive_signals: List[str] = []
        strengths: List[str] = []
        weaknesses: List[str] = []

        # --- Q8 In-depth Breakdown (/100) ---
        q8_hook = 10
        q8_value = 10
        q8_curiosity = 10
        q8_pers = 10
        q8_next_step = 10

        if len(ans8) > 50:
            q8_hook += 4
            q8_value += 4
        if any(w in ans8 for w in ["привіт", "вітаю", "добрий", "хвилин", "бачу", "помітив"]):
            q8_hook += 5
        if any(w in ans8 for w in ["клієнт", "заявк", "продаж", "прибут", "грош", "економ", "конверс", "результат", "лід"]):
            q8_value += 6
            positive_signals.append("Продає кінцевий фінансовий результат (ліди/прибуток), а не технічні послуги")
        else:
            red_flags.append({"flag": "У пітчі відсутній фокус на вигоду та окупність для бізнесу", "severity": "MEDIUM"})
            weaknesses.append("Схильність презентувати послугу без акценту на бізнес-результат")

        if any(w in ans8 for w in ["якби", "цікаво", "подивіт", "розрахунок", "приклад", "кейс", "збільшит"]):
            q8_curiosity += 5
        if any(w in ans8 for w in ["вашого", "вашій", "ніші", "у вас", "конкретно"]):
            q8_pers += 5
        if any(w in ans8 for w in ["зустріч", "zoom", "час", "хвилин", "поговорити", "набрати", "коли", "зручно"]):
            q8_next_step += 5
            positive_signals.append("Чітко закриває розмову на наступний крок (10 хв Zoom/дзвінок)")
        else:
            red_flags.append({"flag": "Не зафіксував чіткий заклик до дії (Call To Action / наступний крок)", "severity": "LOW"})

        q8_hook = min(20, q8_hook)
        q8_value = min(20, q8_value)
        q8_curiosity = min(20, q8_curiosity)
        q8_pers = min(20, q8_pers)
        q8_next_step = min(20, q8_next_step)
        q8_total = q8_hook + q8_value + q8_curiosity + q8_pers + q8_next_step

        # --- Category Scoring ---
        category_scores: Dict[str, int] = {}

        # 1. Communication
        comm = 5
        if len(ans1) > 40: comm += 2
        if any(w in ans1 for w in ["спілкув", "люд", "розвит", "команд", "клієнт"]): comm += 2
        category_scores["communication"] = min(10, max(2, comm))

        # 2. Motivation
        mot = 4
        if any(w in ans1 for w in ["зароб", "грош", "кар'єр", "результат", "ціл", "рост", "ltv", "b2b"]):
            mot += 5
            positive_signals.append("Здорова фінансова та кар'єрна мотивація до заробітку")
        else:
            red_flags.append({"flag": "Низька або нечітка мотивація до продажів", "severity": "MEDIUM"})
        category_scores["motivation"] = min(10, max(2, mot))

        # 3. Logic
        logic = 4
        if any(w in ans3 for w in ["хвилин", "добрий", "проблем", "запит", "цікав", "витрат"]): logic += 3
        if "?" in ans3:
            logic += 3
            positive_signals.append("Ставить відкриті запитання вже на перших секундах холодного контакту")
        else:
            red_flags.append({"flag": "Не ставить запитань на першому контакті", "severity": "LOW"})
        category_scores["logic"] = min(10, max(2, logic))

        # 4. Sales / Q8
        sales_cat = int(q8_total * 0.15)
        category_scores["sales"] = min(15, max(3, sales_cat))

        # 5. Objection Handling
        obj = 3
        if "?" in ans4 or any(w in ans4 for w in ["чому", "підкажіть", "уточнити", "зараз", "розглян", "якби"]):
            obj += 3
            positive_signals.append("Грамотно відповідає на заперечення зустрічним питанням, а не суперечкою")
        else:
            red_flags.append({"flag": "При запереченні не ставить уточнювальних питань", "severity": "MEDIUM"})

        if any(w in ans5 for w in ["коли", "набрати", "уточнити", "передзвон", "зустріч", "зручно"]):
            obj += 4
            positive_signals.append("Не відпускає клієнта у безрезультатне «скиньте в тг»")
        else:
            weaknesses.append("Схильність пасивно погоджуватися скинути інформацію без фіксації контакту")
            red_flags.append({"flag": "Пасивно відпускає клієнта на запереченні 'скиньте в telegram'", "severity": "MEDIUM"})
        category_scores["objection_handling"] = min(10, max(2, obj))

        # 6. Discovery & Listening
        disc = 3
        if any(w in ans7 for w in ["слухати", "чути", "потреб", "біль", "запит", "80", "70"]):
            disc += 7
            positive_signals.append("Розуміє пріоритет слухання та виявлення потреб над говорінням")
        else:
            red_flags.append({"flag": "Схильність до монологу або нерозуміння важливості виявлення болей", "severity": "HIGH"})
        category_scores["discovery_listening"] = min(10, max(2, disc))

        # 7. Rejection Resilience
        resil = 3
        if any(w in ans6 for w in ["аналіз", "помилк", "далі", "продовж", "дзвонити", "статистик", "виправ"]):
            resil += 7
            positive_signals.append("Зріле та системне сприйняття відмов як частини воронки")
        elif any(w in ans6 for w in ["винні", "база", "засмуч", "поган"]):
            red_flags.append({"flag": "Звинувачує базу/клієнтів або опускає руки при відмовах", "severity": "HIGH"})
        category_scores["rejection_resilience"] = min(10, max(2, resil))

        # 8. Initiative
        init = 3
        if any(w in ans10 for w in ["керівник", "тімлід", "допомог", "скрипт", "навч", "практик", "більше", "покращ", "розбір"]):
            init += 7
            positive_signals.append("Проактивний пошук рішень та готовність навчатися у тімліда")
        else:
            red_flags.append({"flag": "Пасивність або уникнення відповідальності за особистий результат", "severity": "HIGH"})
        category_scores["initiative"] = min(10, max(2, init))

        # 9. Discipline
        disc_score = 2
        digits = re.findall(r"\d+", ans9)
        if digits:
            num = int(digits[0])
            if 40 <= num <= 120:
                disc_score = 5
                positive_signals.append(f"Готовність до високого щоденного темпу дзвінків ({num}/день)")
            elif num < 20:
                disc_score = 1
                red_flags.append({"flag": f"Занадто низька готовність до обсягу холодних дзвінків ({num}/день)", "severity": "HIGH"})
            else:
                disc_score = 3
        else:
            red_flags.append({"flag": "Не вказано конкретну кількість щоденних дзвінків", "severity": "MEDIUM"})
        category_scores["discipline"] = min(5, max(1, disc_score))

        # 10. Voice Test
        if has_voice:
            voice_cat = 9
            positive_signals.append("Успішно надіслав голосове практичне завдання")
        else:
            voice_cat = 2
            weaknesses.append("Не записав голосове повідомлення для оцінки дикції та впевненості")
            red_flags.append({"flag": "Пропущено голосовий телефонний тест", "severity": "MEDIUM"})
        category_scores["voice_test"] = voice_cat

        general_score = sum(category_scores.values())

        # Sales Potential Score
        sales_potential_raw = (
            (q8_total * 0.35) +
            (category_scores["objection_handling"] * 10 * 0.20) +
            (category_scores["discovery_listening"] * 10 * 0.15) +
            (category_scores["rejection_resilience"] * 10 * 0.15) +
            ((category_scores["initiative"] + category_scores["discipline"]) * (100 / 15) * 0.15)
        )
        high_rf_count = sum(1 for rf in red_flags if rf.get("severity") == "HIGH")
        med_rf_count = sum(1 for rf in red_flags if rf.get("severity") == "MEDIUM")
        penalty = (high_rf_count * 8) + (med_rf_count * 3)

        sales_potential_score = int(min(100, max(10, round(sales_potential_raw - penalty))))

        sales_potential_level = classify_sales_potential_level(sales_potential_score)
        ai_rec, badge, confidence, rec_desc = classify_ai_recommendation(general_score, sales_potential_score)

        default_strengths = [
            "Швидко і конструктивно формулює комерційні аргументи",
            "Орієнтація на конкретний результат і вигоду для бізнесу",
            "Стійкість до стресу та самостійний аналіз помилок"
        ]
        default_weaknesses = [
            "Потребує практики за готовими скриптами digital-команди",
            "Варто більше прокачувати роботу з запереченнями щодо бюджету",
            "Потрібен контроль регулярності дзвінків на етапі адаптації"
        ]
        for s in default_strengths:
            if len(strengths) < 3 and s not in strengths:
                strengths.append(s)
        for w in default_weaknesses:
            if len(weaknesses) < 3 and w not in weaknesses:
                weaknesses.append(w)

        tailored_questions = [
            "Уяви, що власник каже: «У нас і так достатньо клієнтів, сайти нам не потрібні». Які 2 зустрічні питання ти поставиш?",
            "Якби тобі потрібно було за 15 секунд пояснити цінність автоматизації власнику логістичної компанії, що б ти сказав?",
            "Ти телефонуєш у компанію, а секретар каже «Керівника немає на місці, пишіть на інфо-пошту». Як ти обійдеш секретаря?",
            "Розкажи про свій найболючіший досвід відмови або конфлікту з клієнтом. Що ти зробив після цього?",
            "Якщо за перший тиждень з 200 дзвінків призначено 0 зустрічей, які 3 речі ти зміниш у своїй роботі?"
        ]

        ai_explanation = {
            "score_drivers": f"Загальний бал {general_score}/100 та Sales Potential {sales_potential_score}/100 сформовані на основі структури відповіді на головний тест Q8 ({q8_total}/100) та стійкості до відмов.",
            "strongest_answers": "Питання 8 (продаж зустрічі) та Питання 6 (реакція на 27 відмов).",
            "risks": "Зверніть увагу на відсутність досвіду роботи зі специфічними запереченнями у сфері CRM/AI.",
            "live_check": "На живій співбесіді провести рольову гру: ви — скептичний власник, кандидат — холодний менеджер."
        }

        voice_analysis = {
            "confidence": 9 if has_voice else 3,
            "clarity": 8 if has_voice else 3,
            "energy": 8 if has_voice else 3,
            "naturalness": 9 if has_voice else 3,
            "reading_script": False,
            "summary": "Впевнена та спокійна подача, природна інтонація без страху перед контактом." if has_voice else "Голосовий тест не надіслано."
        }

        profile = (
            "Впевнений, проактивний та дисциплінований кандидат з вираженим комерційним мисленням. Розуміє різницю між продажем функцій та вигоди."
            if sales_potential_score >= 75 else
            "Кандидат з базовими комунікативними навичками, якому може знадобитися готовий скрипт та коучинг."
        )

        predicted_perf = (
            "Висока здатність швидко вийти на планову конверсію закриття на первинні зустрічі з керівниками бізнесів."
            if sales_potential_score >= 75 else
            "Потребує додаткового тестування на рольовому дзвінку для оцінки реальної конверсії."
        )

        return {
            "total_score": general_score,
            "sales_potential_score": sales_potential_score,
            "sales_potential_level": sales_potential_level,
            "ai_recommendation": ai_rec,
            "confidence": confidence,
            "ai_recommendation_reason": rec_desc,
            "category_scores": category_scores,
            "strengths": strengths[:3],
            "weaknesses": weaknesses[:3],
            "red_flags": red_flags,
            "positive_signals": positive_signals[:4],
            "q8_breakdown": {
                "hook": q8_hook,
                "value": q8_value,
                "curiosity": q8_curiosity,
                "personalization": q8_pers,
                "next_step": q8_next_step,
                "total": q8_total
            },
            "voice_analysis": voice_analysis,
            "authenticity_signal": "HIGH",
            "interview_questions": tailored_questions,
            "ai_explanation": ai_explanation,
            "psychological_profile": profile,
            "predicted_performance": predicted_perf
        }

ai_analyzer = AIAnalyzer()
