# services/signal_qualification_agent.py

import os
import json
import re
from datetime import datetime, timedelta
from loguru import logger

from storage.db.database import SessionLocal
from storage.models.mobile_signal import MobileSignal
from storage.models.qualified_signal import QualifiedSignal
from services.supabase_repo import SupabaseRepo
from services.rules_engine import RulesEngine

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FAMILY_FILE = os.path.join(PROJECT_ROOT, "config", "family_context.json")
DOMAINS_FILE = os.path.join(PROJECT_ROOT, "config", "high_value_domains.json")
RULES_FILE = os.path.join(PROJECT_ROOT, "config", "qualification_rules.json")


class SignalQualificationAgent:
    """
    Module 2A.2 - Business Context Layer
    Handles deterministic qualification, filters, scoring, family context boosts,
    high-value domains, and financial preservation rules.
    """

    _family_context = None
    _high_value_domains = None
    _qualification_rules = None

    @classmethod
    def load_configs(cls):
        """Loads configuration json files dynamically."""
        for path, var_name in [
            (FAMILY_FILE, "_family_context"),
            (DOMAINS_FILE, "_high_value_domains"),
            (RULES_FILE, "_qualification_rules")
        ]:
            if os.path.exists(path):
                try:
                    with open(path, "r") as f:
                        setattr(cls, var_name, json.load(f) or {})
                    logger.info(f"SignalQualificationAgent: Loaded config from {path}")
                except Exception as e:
                    logger.error(f"Error loading config {path}: {e}")
                    setattr(cls, var_name, {})
            else:
                logger.warning(f"Config file not found at {path}. Using empty fallback.")
                setattr(cls, var_name, {})

    @classmethod
    def parse_timestamp(cls, ts_str: str) -> datetime:
        """Parses original string/epoch timestamp into datetime."""
        ts_str = str(ts_str).strip()
        try:
            if ts_str.isdigit():
                val = int(ts_str)
                if val > 1e11:
                    return datetime.utcfromtimestamp(val / 1000.0)
                else:
                    return datetime.utcfromtimestamp(val)
            else:
                return datetime.fromisoformat(ts_str.replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            return datetime.utcnow()

    @classmethod
    def check_is_duplicate(cls, db_session, source: str, sender: str, message: str, timestamp: datetime) -> bool:
        """Consolidates cross-channel duplicate check in the last 48 hours."""
        cutoff = datetime.utcnow() - timedelta(days=2)
        
        recent_matches = db_session.query(QualifiedSignal).filter(
            QualifiedSignal.created_at >= cutoff
        ).all()

        message_clean = message.strip().lower()
        for sig in recent_matches:
            if sig.message.strip().lower() == message_clean:
                return True

        amount_match = re.search(r"(?:rs\.?|inr|\$)\s?([\d,]+(?:\.\d+)?)", message_clean)
        if amount_match:
            amt = float(amount_match.group(1).replace(",", ""))
            for sig in recent_matches:
                if sig.source == source:
                    sig_amt_match = re.search(r"(?:rs\.?|inr|\$)\s?([\d,]+(?:\.\d+)?)", sig.message.lower())
                    if sig_amt_match:
                        sig_amt = float(sig_amt_match.group(1).replace(",", ""))
                        if abs(amt - sig_amt) < 0.01:
                            if sig.sender.strip().lower() == sender.strip().lower():
                                return True
        return False

    @classmethod
    def qualify_signal(cls, db_session, signal_id: str, source: str, sender: str, message: str, raw_ts_str: str) -> QualifiedSignal:
        """
        Determines the qualification status (QUALIFIED, REVIEW, REJECTED)
        and scores the signal (0 - 100) using family boosts and high-value domains.
        """
        if cls._qualification_rules is None:
            cls.load_configs()

        timestamp = cls.parse_timestamp(raw_ts_str)
        message_lower = message.lower().strip()
        sender_lower = sender.lower().strip()
        source_lower = source.lower().strip()

        # Load configurations
        rules = cls._qualification_rules
        thresholds = rules.get("thresholds", {"rejected": 20, "review": 60, "qualified": 100})
        boosts_cfg = rules.get("boosts", {"family_context": 30, "high_value_domain": 30})
        preservation_topics = rules.get("preservation", {}).get("financial_topics", [])

        # Start with base score of 40 (REVIEW default status)
        score = 40
        status = "QUALIFIED"
        reason = None
        is_rejected = False

        # 1. Age Filters (SMS & Email <= 90 days, WhatsApp allowed)
        if source_lower in ("sms", "email"):
            cutoff = datetime.utcnow() - timedelta(days=90)
            if timestamp < cutoff:
                score = 0
                is_rejected = True
                status = "REJECTED"
                reason = "STALE_SIGNAL"

        # 2. Duplicate Check
        if not is_rejected:
            if cls.check_is_duplicate(db_session, source, sender, message, timestamp):
                score = 0
                is_rejected = True
                status = "REJECTED"
                reason = "DUPLICATE_SIGNAL"

        # 3. OTP Keyword Rejection
        if not is_rejected:
            otp_keywords = ["otp", "verification code", "one-time password", "one time password", "verification password", "securesubmit"]
            if any(kw in message_lower for kw in otp_keywords):
                score = 10
                is_rejected = True
                status = "REJECTED"
                reason = "OTP"

        # 4. WhatsApp System & Media Logs Rejection
        if not is_rejected and source_lower == "whatsapp":
            whatsapp_noise = [
                "checking for new messages", "whatsapp is running", "this message was deleted",
                "you deleted this message", "incoming voice call", "incoming video call",
                "missed voice call", "missed video call", "photo", "video", "audio", "sticker", "gif"
            ]
            if any(term in message_lower for term in whatsapp_noise) or message_lower in whatsapp_noise:
                score = 5
                is_rejected = True
                status = "REJECTED"
                reason = "SYSTEM_NOTIFICATION"

        # 5. SMS Overlay / Noise Keywords
        if not is_rejected and source_lower == "sms":
            sms_noise = ["tap to view", "click here to view", "truecaller", "overlay notification"]
            if any(term in message_lower for term in sms_noise):
                score = 5
                is_rejected = True
                status = "REJECTED"
                reason = "SYSTEM_NOTIFICATION"

        # 6. Telecom plan / Data limit alerts
        if not is_rejected:
            telecom_keywords = [
                "daily high speed data limit", "data limit usage exceeded", "90% data alert",
                "data balance", "recharge successful for", "pack validity", "validity of your plan",
                "recharge today", "recharge pending", "recharge now"
            ]
            if any(kw in message_lower for kw in telecom_keywords):
                score = 15
                is_rejected = True
                status = "REJECTED"
                reason = "SYSTEM_NOTIFICATION"

        # 7. Promotional Spam / Ads
        if not is_rejected:
            # Only reject as promo if no financial transaction keywords match
            is_txn = any(kw in message_lower for kw in ["debited", "credited", "spent", "card ending", "received rs", "transacted"])
            if not is_txn:
                promo_keywords = [
                    "pre-approved loan", "apply now for credit card", "instant personal loan",
                    "click to apply", "limited time offer", "exclusive discount", "congratulations! you win",
                    "spin the wheel", "use code to get discount", "flat off on order"
                ]
                if any(kw in message_lower for kw in promo_keywords):
                    score = 15
                    is_rejected = True
                    status = "REJECTED"
                    reason = "PROMOTION"

        # 7.5 Financial Advisory Rejection
        if not is_rejected:
            advisory_keywords = [
                "never share", "do not share", "dont share", "don't share",
                "never disclose", "do not disclose",
                "update kyc", "kyc update", "verify kyc", "kyc verification",
                "beware of", "fraud alert", "safe banking", "security tips", "safety tips",
                "stay safe", "avoid clicking", "fake message", "scam alert", "scam warning",
                "never respond", "rbi kehta hai", "online safety"
            ]
            if any(adv in message_lower for adv in advisory_keywords):
                score = 10
                is_rejected = True
                status = "REJECTED"
                reason = "FINANCIAL_ADVISORY"

        # 8. Group / Community Review Check (e.g. Badminton, Apartment Groups)
        if not is_rejected and status != "REVIEW":
            group_keywords = ["badminton", "apartment", "association", "community", "gate entry", "visitor alert"]
            if any(kw in message_lower for kw in group_keywords):
                score = 45
                status = "REVIEW"
                reason = "LOW_VALUE_SIGNAL"

        # 9. RulesEngine Topics Ignore check
        if not is_rejected and status != "REVIEW":
            if RulesEngine.should_ignore_signal(message):
                score = 15
                is_rejected = True
                status = "REJECTED"
                reason = "LOW_VALUE_SIGNAL"

        # 10. Business Context Boosting (Family & High-Value Domains)
        if not is_rejected and status != "REVIEW":
            # Family Context Boost
            family_cfg = cls._family_context
            family_keywords = family_cfg.get("keywords", [])
            family_names = [family_cfg.get("spouse", "")] + family_cfg.get("children", [])
            all_family_terms = [t.lower() for t in (family_keywords + family_names) if t]
            
            has_family_match = False
            for term in all_family_terms:
                pattern = r'\b' + re.escape(term) + r'\b'
                if re.search(pattern, message_lower) or re.search(pattern, sender_lower):
                    has_family_match = True
                    break
            
            if has_family_match:
                score += boosts_cfg.get("family_context", 30)

            # High-Value Domain Boost
            domains_cfg = cls._high_value_domains
            domain_matched = False
            for domain, keywords in domains_cfg.items():
                for kw in keywords:
                    pattern = r'\b' + re.escape(kw.lower()) + r'\b'
                    if re.search(pattern, message_lower) or re.search(pattern, sender_lower):
                        domain_matched = True
                        break
                if domain_matched:
                    break
            
            if domain_matched:
                score += boosts_cfg.get("high_value_domain", 30)

            score = min(score, 90)

        # Apply thresholds dynamically to compute final status
        if not is_rejected:
            if score <= thresholds.get("rejected", 20):
                status = "REJECTED"
            elif score <= thresholds.get("review", 59):
                status = "REVIEW"
            else:
                status = "QUALIFIED"

        # Financial Preservation Override
        if status == "REJECTED" and reason not in ("STALE_SIGNAL", "DUPLICATE_SIGNAL", "FINANCIAL_ADVISORY"):
            if any(term in message_lower for term in preservation_topics):
                status = "REVIEW"
                score = thresholds.get("rejected", 20) + 5  # Score 25
                reason = "LOW_VALUE_SIGNAL"

        # Save to SQLite QualifiedSignals
        qual_obj = QualifiedSignal(
            signal_id=str(signal_id),
            source=source,
            sender=sender,
            message=message,
            timestamp=timestamp,
            qualification_score=score,
            qualification_status=status,
            qualification_reason=reason
        )
        db_session.add(qual_obj)
        db_session.commit()

        # Sync to Supabase Postgres (Source of Truth)
        SupabaseRepo.create_qualified_signal(
            signal_id=str(signal_id),
            source=source,
            sender=sender,
            message=message,
            timestamp=timestamp,
            qualification_score=score,
            qualification_status=status,
            qualification_reason=reason
        )

        return qual_obj

    @classmethod
    def qualify_all_unprocessed_signals(cls) -> dict:
        """
        Scans all unprocessed raw signals in SQLite, qualifies them,
        and returns a stats overview dictionary.
        """
        db = SessionLocal()
        try:
            unprocessed = db.query(MobileSignal).filter(MobileSignal.processed == False).all()
            if not unprocessed:
                logger.info("SignalQualificationAgent: No unprocessed mobile signals.")
                return {"processed": 0, "qualified": 0, "review": 0, "rejected": 0, "reasons": {}}

            total = len(unprocessed)
            qualified = 0
            review = 0
            rejected = 0
            reasons = {}

            for msg in unprocessed:
                res = cls.qualify_signal(
                    db_session=db,
                    signal_id=str(msg.id),
                    source=msg.source,
                    sender=msg.sender,
                    message=msg.message,
                    raw_ts_str=msg.mobile_timestamp
                )

                if res.qualification_status == "QUALIFIED":
                    qualified += 1
                elif res.qualification_status == "REVIEW":
                    review += 1
                    msg.processed = True
                    db.add(msg)
                elif res.qualification_status == "REJECTED":
                    rejected += 1
                    msg.processed = True
                    db.add(msg)
                    r = res.qualification_reason or "UNKNOWN"
                    reasons[r] = reasons.get(r, 0) + 1

            db.commit()
            
            stats = {
                "processed": total,
                "qualified": qualified,
                "review": review,
                "rejected": rejected,
                "reasons": reasons
            }
            logger.success(f"SignalQualificationAgent stats: {stats}")
            return stats

        finally:
            db.close()
