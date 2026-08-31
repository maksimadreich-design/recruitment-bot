import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
import aiosqlite

from config import config
from database.models import Candidate, AIRecommendation, OwnerDecision
from scoring.compensation import (
    get_commission_rate,
    evaluate_activity_bonus_status,
    calculate_total_earnings
)

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = config.DATABASE_PATH):
        self.db_path = db_path

    async def init_db(self):
        """Initialize SQLite database tables, indexes, and apply migrations."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS candidates (
                    candidate_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL UNIQUE,
                    username TEXT,
                    name TEXT,
                    phone TEXT,
                    answers TEXT,
                    voice_file_id TEXT,
                    score INTEGER,
                    sales_potential_score INTEGER,
                    sales_potential_level TEXT,
                    category_scores TEXT,
                    ai_recommendation TEXT NOT NULL DEFAULT 'POTENTIAL',
                    ai_recommendation_reason TEXT,
                    confidence TEXT,
                    strengths TEXT,
                    weaknesses TEXT,
                    red_flags TEXT,
                    positive_signals TEXT,
                    q8_breakdown TEXT,
                    voice_analysis TEXT,
                    authenticity_signal TEXT,
                    interview_questions TEXT,
                    ai_explanation TEXT,
                    psychological_profile TEXT,
                    predicted_performance TEXT,
                    owner_decision TEXT NOT NULL DEFAULT 'PENDING',
                    decision_admin_id INTEGER,
                    decision_timestamp TIMESTAMP,
                    terms_accepted BOOLEAN DEFAULT 0,
                    terms_accepted_at TIMESTAMP,
                    activity_contacts_current_week INTEGER DEFAULT 0,
                    activity_week_start TEXT,
                    activity_week_end TEXT,
                    activity_bonus_active BOOLEAN DEFAULT 0,
                    activity_bonus_active_until TEXT,
                    activity_contacts_last_week INTEGER DEFAULT 0,
                    sales_current_month INTEGER DEFAULT 0,
                    sales_revenue_current_month REAL DEFAULT 0.0,
                    commission_rate_current_month REAL DEFAULT 0.35,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_candidates_tg ON candidates(telegram_id);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_candidates_ai_rec ON candidates(ai_recommendation);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_candidates_owner_dec ON candidates(owner_decision);")
            await db.commit()

            await self._run_migrations(db)
            logger.info("Database initialized & migrated successfully at %s", self.db_path)

    async def _run_migrations(self, db: aiosqlite.Connection):
        """Ensure all columns exist for backward compatibility."""
        cursor = await db.execute("PRAGMA table_info(candidates)")
        existing_cols = {row[1] for row in await cursor.fetchall()}

        new_columns = {
            "ai_recommendation": "TEXT DEFAULT 'POTENTIAL'",
            "ai_recommendation_reason": "TEXT",
            "owner_decision": "TEXT DEFAULT 'PENDING'",
            "decision_admin_id": "INTEGER",
            "decision_timestamp": "TIMESTAMP",
            "sales_potential_score": "INTEGER",
            "sales_potential_level": "TEXT",
            "confidence": "TEXT",
            "red_flags": "TEXT",
            "positive_signals": "TEXT",
            "q8_breakdown": "TEXT",
            "voice_analysis": "TEXT",
            "authenticity_signal": "TEXT",
            "interview_questions": "TEXT",
            "ai_explanation": "TEXT",
            "terms_accepted": "BOOLEAN DEFAULT 0",
            "terms_accepted_at": "TIMESTAMP",
            "activity_contacts_current_week": "INTEGER DEFAULT 0",
            "activity_week_start": "TEXT",
            "activity_week_end": "TEXT",
            "activity_bonus_active": "BOOLEAN DEFAULT 0",
            "activity_bonus_active_until": "TEXT",
            "activity_contacts_last_week": "INTEGER DEFAULT 0",
            "sales_current_month": "INTEGER DEFAULT 0",
            "sales_revenue_current_month": "REAL DEFAULT 0.0",
            "commission_rate_current_month": "REAL DEFAULT 0.35"
        }

        for col_name, col_type in new_columns.items():
            if col_name not in existing_cols:
                try:
                    await db.execute(f"ALTER TABLE candidates ADD COLUMN {col_name} {col_type};")
                    await db.commit()
                except Exception as e:
                    logger.debug("Column migration note (%s): %s", col_name, e)

    async def get_candidate_by_tg_id(self, telegram_id: int) -> Optional[Candidate]:
        """Fetch candidate by Telegram ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM candidates WHERE telegram_id = ?", (telegram_id,))
            row = await cursor.fetchone()
            if not row:
                return None
            return self._row_to_candidate(row)

    async def get_candidate_by_id(self, candidate_id: int) -> Optional[Candidate]:
        """Fetch candidate by primary key candidate_id."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM candidates WHERE candidate_id = ?", (candidate_id,))
            row = await cursor.fetchone()
            if not row:
                return None
            return self._row_to_candidate(row)

    async def create_or_start_candidate(self, telegram_id: int, username: Optional[str], name: Optional[str] = None) -> Candidate:
        """Create a new candidate in initial PENDING state."""
        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO candidates (telegram_id, username, name, owner_decision, created_at, updated_at, answers)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(telegram_id) DO UPDATE SET
                    username = excluded.username,
                    name = COALESCE(excluded.name, candidates.name),
                    updated_at = excluded.updated_at
            """, (telegram_id, username, name, OwnerDecision.PENDING, now, now, json.dumps({})))
            await db.commit()
        return await self.get_candidate_by_tg_id(telegram_id)

    async def record_terms_acceptance(self, telegram_id: int, accepted: bool) -> bool:
        """Record candidate terms acceptance and formatted timestamp."""
        now_dt = datetime.now().strftime("%d.%m.%Y %H:%M")
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                UPDATE candidates SET
                    terms_accepted = ?,
                    terms_accepted_at = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE telegram_id = ?
            """, (1 if accepted else 0, now_dt if accepted else None, telegram_id))
            await db.commit()
            return cursor.rowcount > 0

    async def save_candidate_full_assessment(
        self,
        telegram_id: int,
        name: str,
        phone: str,
        answers: Dict[str, Any],
        voice_file_id: Optional[str],
        score: int,
        sales_potential_score: int,
        sales_potential_level: str,
        category_scores: Dict[str, int],
        ai_recommendation: str,
        ai_recommendation_reason: str,
        confidence: str,
        strengths: List[str],
        weaknesses: List[str],
        red_flags: List[Dict[str, str]],
        positive_signals: List[str],
        q8_breakdown: Dict[str, int],
        voice_analysis: Dict[str, Any],
        authenticity_signal: str,
        interview_questions: List[str],
        ai_explanation: Dict[str, Any],
        psychological_profile: str,
        predicted_performance: str,
        terms_accepted: bool = True,
        terms_accepted_at: Optional[str] = None
    ) -> Candidate:
        """Save full interview responses, AI evaluation, and terms acceptance to database."""
        now = datetime.utcnow().isoformat()
        terms_time = terms_accepted_at or datetime.now().strftime("%d.%m.%Y %H:%M")
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE candidates SET
                    name = ?,
                    phone = ?,
                    answers = ?,
                    voice_file_id = ?,
                    score = ?,
                    sales_potential_score = ?,
                    sales_potential_level = ?,
                    category_scores = ?,
                    ai_recommendation = ?,
                    ai_recommendation_reason = ?,
                    confidence = ?,
                    strengths = ?,
                    weaknesses = ?,
                    red_flags = ?,
                    positive_signals = ?,
                    q8_breakdown = ?,
                    voice_analysis = ?,
                    authenticity_signal = ?,
                    interview_questions = ?,
                    ai_explanation = ?,
                    psychological_profile = ?,
                    predicted_performance = ?,
                    terms_accepted = ?,
                    terms_accepted_at = COALESCE(terms_accepted_at, ?),
                    owner_decision = 'PENDING',
                    updated_at = ?
                WHERE telegram_id = ?
            """, (
                name,
                phone,
                json.dumps(answers, ensure_ascii=False),
                voice_file_id,
                score,
                sales_potential_score,
                sales_potential_level,
                json.dumps(category_scores, ensure_ascii=False),
                ai_recommendation,
                ai_recommendation_reason,
                confidence,
                json.dumps(strengths, ensure_ascii=False),
                json.dumps(weaknesses, ensure_ascii=False),
                json.dumps(red_flags, ensure_ascii=False),
                json.dumps(positive_signals, ensure_ascii=False),
                json.dumps(q8_breakdown, ensure_ascii=False),
                json.dumps(voice_analysis, ensure_ascii=False),
                authenticity_signal,
                json.dumps(interview_questions, ensure_ascii=False),
                json.dumps(ai_explanation, ensure_ascii=False),
                psychological_profile,
                predicted_performance,
                1 if terms_accepted else 0,
                terms_time,
                now,
                telegram_id
            ))
            await db.commit()
        return await self.get_candidate_by_tg_id(telegram_id)

    async def set_owner_decision(self, candidate_id: int, decision: str, admin_id: Optional[int] = None) -> bool:
        """Update OWNER_DECISION by admin."""
        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                UPDATE candidates SET
                    owner_decision = ?,
                    decision_admin_id = ?,
                    decision_timestamp = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE candidate_id = ?
            """, (decision, admin_id, now, candidate_id))
            await db.commit()
            return cursor.rowcount > 0

    # --- Manager Activity & Commission Helpers ---

    async def record_manager_activity_contacts(self, candidate_id: int, added_contacts: int = 1) -> Optional[Candidate]:
        """Record confirmed outbound cold contacts for the working week."""
        cand = await self.get_candidate_by_id(candidate_id)
        if not cand:
            return None

        current = (cand.activity_contacts_current_week or 0) + added_contacts
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE candidates SET
                    activity_contacts_current_week = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE candidate_id = ?
            """, (current, candidate_id))
            await db.commit()
        return await self.get_candidate_by_id(candidate_id)

    async def evaluate_and_close_weekly_activity(self, candidate_id: int) -> Optional[Candidate]:
        """
        Calculates whether 40+ contacts were achieved in the working week.
        Activates bonus for next week if contacts >= 40.
        """
        cand = await self.get_candidate_by_id(candidate_id)
        if not cand:
            return None

        contacts_done = cand.activity_contacts_current_week or 0
        is_bonus_active = evaluate_activity_bonus_status(contacts_done)
        
        next_week_until = (datetime.now() + timedelta(days=7)).strftime("%d.%m.%Y") if is_bonus_active else None

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE candidates SET
                    activity_contacts_last_week = ?,
                    activity_contacts_current_week = 0,
                    activity_bonus_active = ?,
                    activity_bonus_active_until = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE candidate_id = ?
            """, (contacts_done, 1 if is_bonus_active else 0, next_week_until, candidate_id))
            await db.commit()
        return await self.get_candidate_by_id(candidate_id)

    async def record_manager_sale(self, candidate_id: int, sale_amount: float) -> Optional[Candidate]:
        """
        Record closed client sale for manager.
        Recalculates commission tier (35% -> 40% -> 45%) for the month.
        """
        cand = await self.get_candidate_by_id(candidate_id)
        if not cand:
            return None

        sales_count = (cand.sales_current_month or 0) + 1
        sales_rev = (cand.sales_revenue_current_month or 0.0) + sale_amount
        commission_rate = get_commission_rate(sales_count)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE candidates SET
                    sales_current_month = ?,
                    sales_revenue_current_month = ?,
                    commission_rate_current_month = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE candidate_id = ?
            """, (sales_count, sales_rev, commission_rate, candidate_id))
            await db.commit()
        return await self.get_candidate_by_id(candidate_id)

    async def reset_candidate(self, telegram_id: int) -> bool:
        """Reset candidate completely allowing them to re-take assessment."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM candidates WHERE telegram_id = ?", (telegram_id,))
            await db.commit()
            return cursor.rowcount > 0

    async def list_all_candidates(self, limit: int = 50) -> List[Candidate]:
        """List all candidates without hiding anyone."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM candidates ORDER BY candidate_id DESC LIMIT ?",
                (limit,)
            )
            rows = await cursor.fetchall()
            return [self._row_to_candidate(r) for r in rows]

    async def list_by_ai_recommendation(self, ai_rec: str, limit: int = 50) -> List[Candidate]:
        """Filter candidates by AI recommendation."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM candidates WHERE ai_recommendation = ? ORDER BY candidate_id DESC LIMIT ?",
                (ai_rec, limit)
            )
            rows = await cursor.fetchall()
            return [self._row_to_candidate(r) for r in rows]

    async def list_by_owner_decision(self, decision: str, limit: int = 50) -> List[Candidate]:
        """Filter candidates by Owner Decision."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM candidates WHERE owner_decision = ? ORDER BY candidate_id DESC LIMIT ?",
                (decision, limit)
            )
            rows = await cursor.fetchall()
            return [self._row_to_candidate(r) for r in rows]

    async def get_top_candidates(self, limit: int = 10) -> List[Candidate]:
        """Get top candidates ordered by sales potential and general score."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM candidates 
                WHERE score IS NOT NULL 
                ORDER BY sales_potential_score DESC, score DESC 
                LIMIT ?
            """, (limit,))
            rows = await cursor.fetchall()
            return [self._row_to_candidate(r) for r in rows]

    async def compare_candidates(self, id1: int, id2: int) -> Tuple[Optional[Candidate], Optional[Candidate]]:
        """Fetch two candidates for side-by-side comparison."""
        c1 = await self.get_candidate_by_id(id1)
        c2 = await self.get_candidate_by_id(id2)
        return c1, c2

    async def get_stats(self) -> Dict[str, Any]:
        """Fetch recruitment statistics cleanly separated by AI Assessment and Owner Decisions."""
        async with aiosqlite.connect(self.db_path) as db:
            # AI Assessment Stats
            async with db.execute("SELECT COUNT(*) FROM candidates WHERE score IS NOT NULL") as cur:
                total_ai = (await cur.fetchone())[0]

            async with db.execute("SELECT COUNT(*) FROM candidates WHERE ai_recommendation = ?", (AIRecommendation.STRONG,)) as cur:
                ai_strong = (await cur.fetchone())[0]

            async with db.execute("SELECT COUNT(*) FROM candidates WHERE ai_recommendation = ?", (AIRecommendation.POTENTIAL,)) as cur:
                ai_potential = (await cur.fetchone())[0]

            async with db.execute("SELECT COUNT(*) FROM candidates WHERE ai_recommendation = ?", (AIRecommendation.WEAK,)) as cur:
                ai_weak = (await cur.fetchone())[0]

            async with db.execute("SELECT COUNT(*) FROM candidates WHERE ai_recommendation = ?", (AIRecommendation.REJECT_RECOMMENDED,)) as cur:
                ai_reject_rec = (await cur.fetchone())[0]

            # Owner Decisions Stats
            async with db.execute("SELECT COUNT(*) FROM candidates WHERE owner_decision = 'PENDING' AND score IS NOT NULL") as cur:
                owner_pending = (await cur.fetchone())[0]

            async with db.execute("SELECT COUNT(*) FROM candidates WHERE owner_decision = ?", (OwnerDecision.INTERVIEW,)) as cur:
                owner_interview = (await cur.fetchone())[0]

            async with db.execute("SELECT COUNT(*) FROM candidates WHERE owner_decision = ?", (OwnerDecision.TEST,)) as cur:
                owner_test = (await cur.fetchone())[0]

            async with db.execute("SELECT COUNT(*) FROM candidates WHERE owner_decision = ?", (OwnerDecision.REJECTED,)) as cur:
                owner_rejected = (await cur.fetchone())[0]

            async with db.execute("SELECT COUNT(*) FROM candidates WHERE owner_decision = ?", (OwnerDecision.RESERVE,)) as cur:
                owner_reserve = (await cur.fetchone())[0]

            async with db.execute("SELECT COUNT(*) FROM candidates WHERE owner_decision = ?", (OwnerDecision.HIRED,)) as cur:
                owner_hired = (await cur.fetchone())[0]

            async with db.execute("SELECT AVG(score) FROM candidates WHERE score IS NOT NULL") as cur:
                avg_row = await cur.fetchone()
                avg_score = round(avg_row[0], 1) if avg_row and avg_row[0] is not None else 0.0

            async with db.execute("SELECT AVG(sales_potential_score) FROM candidates WHERE sales_potential_score IS NOT NULL") as cur:
                avg_sales_row = await cur.fetchone()
                avg_sales_score = round(avg_sales_row[0], 1) if avg_sales_row and avg_sales_row[0] is not None else 0.0

            return {
                "ai": {
                    "total": total_ai,
                    "strong": ai_strong,
                    "potential": ai_potential,
                    "weak": ai_weak,
                    "reject_recommended": ai_reject_rec,
                    "avg_score": avg_score,
                    "avg_sales_score": avg_sales_score
                },
                "owner": {
                    "pending": owner_pending,
                    "interview": owner_interview,
                    "test": owner_test,
                    "rejected": owner_rejected,
                    "reserve": owner_reserve,
                    "hired": owner_hired
                }
            }

    def _row_to_candidate(self, row: aiosqlite.Row) -> Candidate:
        def parse_json(val: Any, default: Any):
            if not val:
                return default
            try:
                return json.loads(val)
            except Exception:
                return default

        keys = row.keys()
        def get_field(key, default=None):
            return row[key] if key in keys else default

        return Candidate(
            candidate_id=get_field("candidate_id"),
            telegram_id=get_field("telegram_id"),
            username=get_field("username"),
            name=get_field("name"),
            phone=get_field("phone"),
            answers=parse_json(get_field("answers"), {}),
            voice_file_id=get_field("voice_file_id"),
            score=get_field("score"),
            sales_potential_score=get_field("sales_potential_score"),
            sales_potential_level=get_field("sales_potential_level"),
            category_scores=parse_json(get_field("category_scores"), {}),
            ai_recommendation=get_field("ai_recommendation") or get_field("recommendation") or AIRecommendation.POTENTIAL,
            ai_recommendation_reason=get_field("ai_recommendation_reason") or get_field("recommendation_reason"),
            confidence=get_field("confidence"),
            strengths=parse_json(get_field("strengths"), []),
            weaknesses=parse_json(get_field("weaknesses"), []),
            red_flags=parse_json(get_field("red_flags"), []),
            positive_signals=parse_json(get_field("positive_signals"), []),
            q8_breakdown=parse_json(get_field("q8_breakdown"), {}),
            voice_analysis=parse_json(get_field("voice_analysis"), {}),
            authenticity_signal=get_field("authenticity_signal"),
            interview_questions=parse_json(get_field("interview_questions"), []),
            ai_explanation=parse_json(get_field("ai_explanation"), {}),
            psychological_profile=get_field("psychological_profile"),
            predicted_performance=get_field("predicted_performance"),
            owner_decision=get_field("owner_decision") or get_field("status") or OwnerDecision.PENDING,
            decision_admin_id=get_field("decision_admin_id"),
            decision_timestamp=get_field("decision_timestamp"),
            terms_accepted=bool(get_field("terms_accepted")),
            terms_accepted_at=get_field("terms_accepted_at"),
            activity_contacts_current_week=get_field("activity_contacts_current_week") or 0,
            activity_week_start=get_field("activity_week_start"),
            activity_week_end=get_field("activity_week_end"),
            activity_bonus_active=bool(get_field("activity_bonus_active")),
            activity_bonus_active_until=get_field("activity_bonus_active_until"),
            activity_contacts_last_week=get_field("activity_contacts_last_week") or 0,
            sales_current_month=get_field("sales_current_month") or 0,
            sales_revenue_current_month=get_field("sales_revenue_current_month") or 0.0,
            commission_rate_current_month=get_field("commission_rate_current_month") or 0.35,
            created_at=get_field("created_at"),
            updated_at=get_field("updated_at")
        )

db = Database()
