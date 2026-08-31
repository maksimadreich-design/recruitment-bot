from typing import Dict, Any, Tuple
from database.models import AIRecommendation

SCORING_CATEGORIES = {
    "communication": {"name": "Комунікація", "max": 10},
    "motivation": {"name": "Мотивація", "max": 10},
    "logic": {"name": "Логіка", "max": 10},
    "sales": {"name": "Продажі / Q8", "max": 15},
    "objection_handling": {"name": "Робота із запереченнями", "max": 10},
    "discovery_listening": {"name": "Слухання / discovery", "max": 10},
    "rejection_resilience": {"name": "Стійкість до відмов", "max": 10},
    "initiative": {"name": "Ініціативність", "max": 10},
    "discipline": {"name": "Дисципліна", "max": 5},
    "voice_test": {"name": "Голосовий тест", "max": 10},
}

MAX_TOTAL_SCORE = 100

def classify_sales_potential_level(sales_score: int) -> str:
    """Returns LOW / MEDIUM / HIGH / VERY HIGH."""
    if sales_score >= 85:
        return "VERY HIGH"
    elif sales_score >= 70:
        return "HIGH"
    elif sales_score >= 55:
        return "MEDIUM"
    else:
        return "LOW"

def classify_ai_recommendation(general_score: int, sales_score: int) -> Tuple[str, str, str, str]:
    """
    Returns (ai_recommendation, badge, confidence, cautious_description):
    - STRONG (General >= 75 & Sales >= 70) -> 🔥 STRONG
    - POTENTIAL (General >= 65 or Sales >= 60) -> 🟢 POTENTIAL
    - WEAK (General >= 50 or Sales >= 45) -> 🟡 WEAK
    - REJECT_RECOMMENDED (Below criteria) -> 🔴 REJECT_RECOMMENDED
    """
    if general_score >= 75 and sales_score >= 70:
        return (
            AIRecommendation.STRONG,
            "🔥 STRONG",
            "HIGH",
            "Кандидат продемонстрував високу відповідність критеріям для холодних продажів digital-послуг."
        )
    elif general_score >= 65 or sales_score >= 60:
        return (
            AIRecommendation.POTENTIAL,
            "🟢 POTENTIAL",
            "MEDIUM",
            "Кандидат має базовий потенціал. Рекомендується перевірити практичні навички під час тестового контакту."
        )
    elif general_score >= 50 or sales_score >= 45:
        return (
            AIRecommendation.WEAK,
            "🟡 WEAK",
            "MEDIUM",
            "Виявлено певні ризики та прогалини в комунікації або роботі із запереченнями."
        )
    else:
        return (
            AIRecommendation.REJECT_RECOMMENDED,
            "🔴 REJECT_RECOMMENDED",
            "HIGH",
            "Кандидат має низьку відповідність поточним критеріям відбору на посаду менеджера холодних продажів."
        )

# Backward compatibility alias
def classify_candidate_tier(general_score: int, sales_score: int):
    rec, badge, conf, desc = classify_ai_recommendation(general_score, sales_score)
    return badge, rec, conf, desc

def classify_candidate(score: int):
    rec, badge, conf, desc = classify_ai_recommendation(score, score)
    return badge, rec, desc
