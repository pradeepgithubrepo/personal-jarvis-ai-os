# services/learning_engine.py

import os
import json
import re
from datetime import datetime
from loguru import logger
from storage.models.financial_event import FinancialEvent
from storage.models.category_correction import CategoryCorrection
from services.rules_engine import RulesEngine


class LearningEngine:
    """
    Milestone 6 - Learning Engine
    Tracks manual category corrections by the user. If a correction threshold (3 times)
    is reached for a merchant/new_category pair, automatically promotes it to user_overrides.json.
    """

    CORRECTION_THRESHOLD = 3
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    OVERRIDES_FILE = os.path.join(PROJECT_ROOT, "config", "user_overrides.json")

    @classmethod
    def correct_category(cls, db_session, event_id: int, new_category: str) -> bool:
        """
        Updates the category of the financial event, tracks the manual correction in the DB,
        and automatically writes to user_overrides.json if the threshold is met.
        Returns True if successful, False otherwise.
        """
        new_category = new_category.strip().upper()
        logger.info(f"Received manual category correction: Event ID {event_id} -> '{new_category}'")

        try:
            # 1. Fetch the financial event
            event = db_session.query(FinancialEvent).filter(FinancialEvent.id == event_id).first()
            if not event:
                logger.warning(f"FinancialEvent ID {event_id} not found in database.")
                return False

            old_category = event.category or "OTHER"
            
            # If the category is already correct, do nothing
            if old_category.upper() == new_category:
                logger.info(f"Event ID {event_id} already has category '{new_category}'. Skipping correction.")
                return True

            # Update database record
            event.category = new_category

            # 2. Normalize and resolve the merchant name for tracking corrections
            merchant = (event.paid_to or "").strip().lower()
            if not merchant or "@" in merchant:
                # Try to parse clean merchant name from event title
                summary_lower = (event.title or "").lower()
                match = re.search(r"(?:spent|debited|payment|pay|sent)\s+(?:on|at|to)\s+([a-zA-Z0-9\s]+)", summary_lower)
                if match:
                    merchant = match.group(1).strip()
                else:
                    # Check if any known merchant keyword is in the title
                    from services.rules_engine import RulesEngine
                    merchant_cats = RulesEngine._rules.get("merchant_categories", {})
                    matched_key = None
                    for key in merchant_cats.keys():
                        if key.lower() in summary_lower:
                            matched_key = key.lower()
                            break
                    
                    if matched_key:
                        merchant = matched_key
                    elif event.paid_to:
                        # Use paid_to if not empty, even if VPA
                        merchant = event.paid_to.strip().lower()
                    else:
                        # Fallback to first word of title
                        merchant = event.title.split()[0].lower() if event.title else "unknown"

            # 3. Fetch or create category correction entry
            correction = db_session.query(CategoryCorrection).filter(
                CategoryCorrection.merchant == merchant,
                CategoryCorrection.new_category == new_category
            ).first()

            if correction:
                correction.correction_count += 1
                correction.updated_at = datetime.utcnow()
                logger.info(f"Incremented correction count for merchant '{merchant}' -> '{new_category}' (Count: {correction.correction_count})")
            else:
                correction = CategoryCorrection(
                    merchant=merchant,
                    new_category=new_category,
                    correction_count=1,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db_session.add(correction)
                logger.info(f"Created new correction entry for merchant '{merchant}' -> '{new_category}' (Count: 1)")

            # 4. Check if the correction count meets the threshold to promote to override
            if correction.correction_count >= cls.CORRECTION_THRESHOLD:
                cls._promote_to_override(merchant, new_category)

            db_session.commit()
            return True

        except Exception as e:
            logger.error(f"Error correcting category: {e}")
            db_session.rollback()
            return False

    @classmethod
    def _promote_to_override(cls, merchant: str, new_category: str):
        """Helper method to append/update user_overrides.json on disk."""
        logger.info(f"Threshold reached ({cls.CORRECTION_THRESHOLD} corrections) for merchant '{merchant}' -> '{new_category}'. Promoting to user_overrides.json...")
        
        overrides_data = {"overrides": {}}
        
        # Load existing overrides
        if os.path.exists(cls.OVERRIDES_FILE):
            try:
                with open(cls.OVERRIDES_FILE, "r") as f:
                    overrides_data = json.load(f) or {"overrides": {}}
            except Exception as e:
                logger.error(f"Error reading overrides file for promotion: {e}")
                overrides_data = {"overrides": {}}

        if "overrides" not in overrides_data:
            overrides_data["overrides"] = {}

        # Set/update the override
        overrides_data["overrides"][merchant] = new_category

        # Write back to disk
        try:
            os.makedirs(os.path.dirname(cls.OVERRIDES_FILE), exist_ok=True)
            with open(cls.OVERRIDES_FILE, "w") as f:
                json.dump(overrides_data, f, indent=2)
            logger.success(f"Successfully promoted override '{merchant}' -> '{new_category}' to {cls.OVERRIDES_FILE}")
            
            # Reload rules engine in-memory
            RulesEngine.reload()
        except Exception as e:
            logger.error(f"Failed to save overrides file: {e}")
