from dataclasses import dataclass
from typing import Optional, Dict, Any, List

class AIRecommendation:
    STRONG = "STRONG"
    POTENTIAL = "POTENTIAL"
    WEAK = "WEAK"
    REJECT_RECOMMENDED = "REJECT_RECOMMENDED"

class OwnerDecision:
    PENDING = "PENDING"
    INTERVIEW = "INTERVIEW"
    TEST = "TEST"
    REJECTED = "REJECTED"
    RESERVE = "RESERVE"
    HIRED = "HIRED"

# Backward compatibility alias
CandidateStatus = OwnerDecision

@dataclass
class Candidate:
    candidate_id: Optional[int]
    telegram_id: int
    username: Optional[str]
    name: Optional[str]
    phone: Optional[str]
    answers: Dict[str, Any]
    voice_file_id: Optional[str]
    score: Optional[int]                            # General Score (0-100)
    sales_potential_score: Optional[int]            # Sales Potential Score (0-100)
    sales_potential_level: Optional[str]            # LOW / MEDIUM / HIGH / VERY HIGH
    category_scores: Optional[Dict[str, int]]
    ai_recommendation: str                          # STRONG / POTENTIAL / WEAK / REJECT_RECOMMENDED
    ai_recommendation_reason: Optional[str]         # Cautious objective rationale
    confidence: Optional[str]                       # HIGH / MEDIUM / LOW
    strengths: Optional[List[str]]
    weaknesses: Optional[List[str]]
    red_flags: Optional[List[Dict[str, str]]]       # [{ "flag": "...", "severity": "HIGH/MEDIUM/LOW" }]
    positive_signals: Optional[List[str]]
    q8_breakdown: Optional[Dict[str, int]]          # { "hook": 18, "value": 17, ... }
    voice_analysis: Optional[Dict[str, Any]]
    authenticity_signal: Optional[str]              # LOW / MEDIUM / HIGH
    interview_questions: Optional[List[str]]        # 5 custom questions
    ai_explanation: Optional[Dict[str, Any]]
    psychological_profile: Optional[str]
    predicted_performance: Optional[str]
    owner_decision: str                             # PENDING / INTERVIEW / TEST / REJECTED / RESERVE / HIRED
    decision_admin_id: Optional[int]                # Telegram ID of admin who made the decision
    decision_timestamp: Optional[str]               # Timestamp of decision
    terms_accepted: Optional[bool]                  # True if candidate accepted working terms
    terms_accepted_at: Optional[str]               # Timestamp when terms were accepted

    # Manager Activity & Commission Tracking
    activity_contacts_current_week: Optional[int] = 0
    activity_week_start: Optional[str] = None
    activity_week_end: Optional[str] = None
    activity_bonus_active: Optional[bool] = False
    activity_bonus_active_until: Optional[str] = None
    activity_contacts_last_week: Optional[int] = 0
    sales_current_month: Optional[int] = 0
    sales_revenue_current_month: Optional[float] = 0.0
    commission_rate_current_month: Optional[float] = 0.35

    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @property
    def status(self) -> str:
        """Alias for owner_decision for backward compatibility."""
        return self.owner_decision

    @property
    def recommendation(self) -> str:
        """Alias for ai_recommendation for backward compatibility."""
        return self.ai_recommendation
