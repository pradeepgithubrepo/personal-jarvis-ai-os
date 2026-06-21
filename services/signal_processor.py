# services/signal_processor.py

import json
import re
from datetime import datetime, timedelta
from loguru import logger
from storage.db.database import SessionLocal
from storage.models.signal import Signal
from storage.models.signal_classification import SignalClassification
from storage.models.task import Task
from storage.models.todo import Todo
from storage.models.financial_event import FinancialEvent
from storage.models.fyi_event import FyiEvent


class SignalProcessor:
    """
    Milestone 1 - Signal Classification Engine
    Milestone 2 - TODO Extraction
    Milestone 3 - Financial Extraction
    Milestone 4 - FYI Extraction
    Classifies every structured signal in the unified 'signals' table
    and extracts actionable TODOs, structured financial events, and FYI notifications.
    """

    @staticmethod
    def classify_signal(signal: Signal, db_session) -> tuple[str, float]:
        """
        Classifies a single signal using deterministic rules.
        Returns a tuple of (category, confidence).
        """
        summary_lower = (signal.summary or "").lower()
        
        # Safely parse raw_json details
        details = {}
        if signal.raw_json:
            try:
                details = json.loads(signal.raw_json) or {}
            except Exception:
                pass

        # Check configuration rules engine first
        from services.rules_engine import RulesEngine
        if RulesEngine.should_ignore_signal(signal.summary or "", signal.raw_json):
            return "IGNORE", 1.0

        # 1. IGNORE RULE (OTP / Ignore priority / Spam)
        if (
            signal.importance == "ignore"
            or signal.signal_type == "otp"
            or "otp" in details
            or "otp_code" in details
        ):
            return "IGNORE", 1.0

        otp_keywords = ["otp", "verification code", "one time password", "security code", "verification password"]
        if any(kw in summary_lower for kw in otp_keywords):
            return "IGNORE", 1.0

        # 2. INSURANCE RULE (Car/bike policy renewal alerts)
        insurance_keywords = [
            "insurance", "renew", "renewal", "policy", "premium", "lic",
            "hdfc ergo", "car insurance", "bike insurance", "motor insurance",
            "kotak life", "policybazaar", "chola ms"
        ]
        if any(kw in summary_lower for kw in insurance_keywords):
            return "INSURANCE", 1.0

        # 3. FINANCIAL RULE (Salary, credit, debit, transactions, bank alerts)
        if (
            signal.signal_type == "financial_transaction"
            or signal.category == "finance"
            or "amount" in details
            or "transaction_type" in details
        ):
            return "FINANCIAL", 1.0

        financial_keywords = [
            "credited", "debited", "spent", "spent on", "card ending",
            "a/c ending", "account ending", "upi", "emi", "salary",
            "payment of", "transaction", "bank", "cashback"
        ]
        if any(kw in summary_lower for kw in financial_keywords):
            return "FINANCIAL", 1.0

        # 4. TODO RULE (Actionable tasks)
        # Check if an associated task exists in the tasks table
        task_exists = db_session.query(Task).filter(
            Task.title == signal.summary,
            Task.source == signal.source
        ).first() is not None

        if (
            task_exists
            or details.get("classification") == "task"
            or (details.get("action_items") and len(details.get("action_items")) > 0)
        ):
            return "TODO", 1.0

        # Heuristic for WhatsApp / personal / school actionable verbs
        if (
            signal.source == "whatsapp"
            or signal.category in ("school", "personal")
            or signal.signal_type in ("school_update", "personal_chat")
        ):
            todo_verbs = [
                "bring", "buy", "call", "send", "submit", "remember",
                "do", "homework", "complete", "remind", "pay before",
                "due on", "action required", "please verify"
            ]
            if any(verb in summary_lower for verb in todo_verbs):
                return "TODO", 1.0

        # 5. FYI RULE (Informational updates)
        fyi_keywords = [
            "circular", "school update", "delivered", "shipped",
            "out for delivery", "family update", "update", "newsletter",
            "notification", "dispatch"
        ]
        if (
            signal.signal_type in ("delivery_update", "shopping_order")
            or signal.category in ("shopping", "education")
            or details.get("classification") == "FYI"
            or any(kw in summary_lower for kw in fyi_keywords)
        ):
            return "FYI", 1.0

        # Default fallback
        return "FYI", 0.8

    @classmethod
    def process_all_signals(cls) -> int:
        """
        Loads all unclassified signals from the signals table,
        classifies them, and saves the classification results.
        Returns the number of signals processed.
        """
        db = SessionLocal()
        try:
            # Query signals that do not have a corresponding entry in signal_classification
            # Using subquery or not exists
            from sqlalchemy import select
            classified_ids = select(SignalClassification.signal_id)
            unclassified_signals = db.query(Signal).filter(Signal.id.not_in(classified_ids)).all()

            logger.info(f"Found {len(unclassified_signals)} unclassified signals.")
            if not unclassified_signals:
                return 0

            processed_count = 0
            for signal in unclassified_signals:
                category, confidence = cls.classify_signal(signal, db)
                
                classification = SignalClassification(
                    signal_id=signal.id,
                    category=category,
                    confidence=confidence,
                    processed_at=datetime.utcnow()
                )
                db.merge(classification)  # Use merge to handle potential races cleanly
                processed_count += 1
                
                logger.debug(
                    f"Classified signal ID {signal.id} "
                    f"-> Category: {category} (Confidence: {confidence})"
                )

            db.commit()
            logger.success(f"Successfully classified {processed_count} signals.")
            return processed_count

        except Exception as e:
            logger.exception(f"Error processing signal classifications: {e}")
            db.rollback()
            raise e
        finally:
            db.close()

    @staticmethod
    def parse_and_normalize_due_date(text: str, created_at: datetime) -> str | None:
        """
        Helper method to deterministically parse and normalize due date from text.
        Supports:
          - "tomorrow" -> (created_at + 1 day) formatted as YYYY-MM-DD
          - YYYY-MM-DD
          - DD-MM-YYYY or DD/MM/YYYY -> YYYY-MM-DD
          - "DD MMM YYYY" or "DD MMM" -> YYYY-MM-DD
        """
        if not text:
            return None
            
        text_lower = text.lower()
        ref_date = created_at if created_at else datetime.utcnow()

        # 1. "tomorrow"
        if "tomorrow" in text_lower:
            due_dt = ref_date + timedelta(days=1)
            return due_dt.strftime("%Y-%m-%d")

        # 2. YYYY-MM-DD
        match_yyyy_mm_dd = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
        if match_yyyy_mm_dd:
            return match_yyyy_mm_dd.group(0)

        # 3. DD-MM-YYYY or DD/MM/YYYY
        match_dd_mm_yyyy = re.search(r"\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b", text)
        if match_dd_mm_yyyy:
            day_str, month_str, year_str = match_dd_mm_yyyy.groups()
            return f"{int(year_str):04d}-{int(month_str):02d}-{int(day_str):02d}"

        # 4. DD MMM YYYY or DD MMM
        months = {
            "jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
            "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12",
            "january": "01", "february": "02", "march": "03", "april": "04", "june": "06",
            "july": "07", "august": "08", "september": "09", "october": "10", "november": "11", "december": "12"
        }
        months_pattern = "|".join(months.keys())
        match_named = re.search(r"\b(\d{1,2})\s+(" + months_pattern + r")(?:\s+(\d{4}))?\b", text_lower)
        if match_named:
            day_str, month_name, year_str = match_named.groups()
            day = f"{int(day_str):02d}"
            month = months[month_name]
            year = year_str if year_str else str(ref_date.year)
            return f"{int(year):04d}-{month}-{day}"

        return None

    @classmethod
    def extract_todos(cls) -> int:
        """
        Extracts TODOs from all signals classified as 'TODO'.
        Only extracts if the signal is not already processed in the todos table.
        """
        db = SessionLocal()
        try:
            # Query signals classified as TODO
            from sqlalchemy import select
            classified_todos = select(SignalClassification.signal_id).where(
                SignalClassification.category == "TODO"
            )
            
            # Find signals that are classified as TODO and not already in todos table
            existing_todo_signal_ids = select(Todo.source_signal_id)
            todo_signals = db.query(Signal).filter(
                Signal.id.in_(classified_todos),
                Signal.id.not_in(existing_todo_signal_ids)
            ).all()

            logger.info(f"Found {len(todo_signals)} new TODO signals to extract.")
            if not todo_signals:
                return 0

            extracted_count = 0
            for signal in todo_signals:
                # Safely parse raw_json details
                details = {}
                if signal.raw_json:
                    try:
                        details = json.loads(signal.raw_json) or {}
                    except Exception:
                        pass

                # Resolve due date deterministically
                due_date = None
                
                # Check 1: tasks table inheritance
                task = db.query(Task).filter(
                    Task.title == signal.summary,
                    Task.source == signal.source
                ).first()
                if task and task.due_date:
                    due_date = cls.parse_and_normalize_due_date(task.due_date, signal.created_at) or task.due_date

                # Check 2: details in raw_json
                if not due_date and details.get("due_date"):
                    candidate_due_date = details.get("due_date")
                    due_date = cls.parse_and_normalize_due_date(candidate_due_date, signal.created_at) or candidate_due_date

                # Check 3: parse from signal summary
                if not due_date:
                    due_date = cls.parse_and_normalize_due_date(signal.summary, signal.created_at)

                # Store Todo
                todo_obj = Todo(
                    title=signal.summary,
                    due_date=due_date,
                    source_signal_id=signal.id,
                    priority=signal.importance,
                    created_at=signal.created_at
                )
                db.add(todo_obj)
                extracted_count += 1
                
                logger.debug(
                    f"Extracted Todo: '{todo_obj.title}' "
                    f"| Due: {todo_obj.due_date} | Priority: {todo_obj.priority}"
                )

            db.commit()
            logger.success(f"Successfully extracted {extracted_count} TODOs.")
            return extracted_count

        except Exception as e:
            logger.exception(f"Error extracting TODOs: {e}")
            db.rollback()
            raise e
        finally:
            db.close()

    @staticmethod
    def parse_amount(val) -> float | None:
        """
        Extracts a clean float amount from an integer, float, or string.
        Strips commas, symbols, and currency handles, and matches the number value.
        """
        if val is None:
            return None
        try:
            if isinstance(val, (int, float)):
                return float(val)
            val_str = str(val).lower().replace(",", "").replace("rs.", "").replace("rs", "").replace("inr", "").replace("$", "").strip()
            match = re.search(r"[-+]?\d*\.\d+|\d+", val_str)
            if match:
                return float(match.group(0))
        except Exception:
            pass
        return None

    @classmethod
    def extract_financial_events(cls) -> int:
        """
        Extracts financial events from all signals classified as 'FINANCIAL' or 'INSURANCE'.
        Only extracts if the signal is not already processed in the financial_events table.
        """
        db = SessionLocal()
        try:
            # Query signals classified as FINANCIAL or INSURANCE
            from sqlalchemy import select
            classified_financials = select(SignalClassification.signal_id).where(
                SignalClassification.category.in_(["FINANCIAL", "INSURANCE"])
            )
            
            # Find signals that are classified as FINANCIAL/INSURANCE and not already in financial_events table
            existing_event_signal_ids = select(FinancialEvent.source_signal_id)
            financial_signals = db.query(Signal).filter(
                Signal.id.in_(classified_financials),
                Signal.id.not_in(existing_event_signal_ids)
            ).all()

            logger.info(f"Found {len(financial_signals)} new financial signals to extract.")
            if not financial_signals:
                return 0

            extracted_count = 0
            for signal in financial_signals:
                # Safely parse raw_json details
                details = {}
                if signal.raw_json:
                    try:
                        details = json.loads(signal.raw_json) or {}
                    except Exception:
                        pass

                # Resolve transaction type
                sig_classification = db.query(SignalClassification).filter(
                    SignalClassification.signal_id == signal.id
                ).first()
                classification_cat = sig_classification.category if sig_classification else None
                
                if classification_cat == "INSURANCE":
                    tx_type = "renewal"
                else:
                    # Look for transaction type in raw json, fallback to checking content/intent
                    details_tx_type = details.get("transaction_type")
                    if details_tx_type:
                        tx_type = str(details_tx_type).lower().strip()
                    else:
                        summary_lower = (signal.summary or "").lower()
                        if "credited" in summary_lower or "received" in summary_lower or "deposit" in summary_lower:
                            tx_type = "credit"
                        else:
                            tx_type = "debit"

                # Parse amount
                amount_candidate = details.get("amount")
                if not amount_candidate:
                    # Try to regex parse amount from summary
                    amount_match = re.search(r"(?:rs\.?|inr|\$)\s?([\d,]+(?:\.\d+)?)", (signal.summary or "").lower())
                    amount_candidate = amount_match.group(1) if amount_match else None
                    
                amount = cls.parse_amount(amount_candidate)

                # Parse currency
                currency = details.get("currency") or "INR"

                # Parse date
                event_date = signal.created_at
                details_date = details.get("due_date") or details.get("delivery_date") or details.get("transaction_date")
                if details_date:
                    normalized_date_str = cls.parse_and_normalize_due_date(details_date, signal.created_at)
                    if normalized_date_str:
                        try:
                            event_date = datetime.strptime(normalized_date_str, "%Y-%m-%d")
                        except Exception:
                            pass

                # Store FinancialEvent
                merchant = details.get("paid_to") or details.get("paid_from") or details.get("merchant") or ""
                vpa = details.get("vpa") or details.get("upi_vpa") or ""
                if not vpa and "@" in merchant:
                    vpa = merchant

                from services.rules_engine import RulesEngine
                spend_category = RulesEngine.categorize_transaction(merchant, vpa, signal.summary or "")

                event_obj = FinancialEvent(
                    title=signal.summary,
                    amount=amount,
                    currency=currency,
                    transaction_type=tx_type,
                    payment_channel=details.get("payment_channel"),
                    paid_to=details.get("paid_to") or merchant,
                    paid_from=details.get("paid_from"),
                    transaction_id=details.get("transaction_id"),
                    event_date=event_date,
                    source_signal_id=signal.id,
                    created_at=signal.created_at,
                    category=spend_category
                )
                db.add(event_obj)
                extracted_count += 1
                
                logger.debug(
                    f"Extracted Financial Event: '{event_obj.title}' "
                    f"| Amount: {event_obj.amount} | Type: {event_obj.transaction_type} "
                    f"| Date: {event_obj.event_date}"
                )

            db.commit()
            logger.success(f"Successfully extracted {extracted_count} financial events.")
            return extracted_count

        except Exception as e:
            logger.exception(f"Error extracting financial events: {e}")
            db.rollback()
            raise e
        finally:
            db.close()

    @classmethod
    def extract_fyi_events(cls) -> int:
        """
        Extracts FYI events from all signals classified as 'FYI'.
        Only extracts if the signal is not already processed in the fyi_events table.
        """
        db = SessionLocal()
        try:
            # Query signals classified as FYI
            from sqlalchemy import select
            classified_fyis = select(SignalClassification.signal_id).where(
                SignalClassification.category == "FYI"
            )
            
            # Find signals that are classified as FYI and not already in fyi_events table
            existing_fyi_signal_ids = select(FyiEvent.source_signal_id)
            fyi_signals = db.query(Signal).filter(
                Signal.id.in_(classified_fyis),
                Signal.id.not_in(existing_fyi_signal_ids)
            ).all()

            logger.info(f"Found {len(fyi_signals)} new FYI signals to extract.")
            if not fyi_signals:
                return 0

            extracted_count = 0
            for signal in fyi_signals:
                # Safely parse raw_json details
                details = {}
                if signal.raw_json:
                    try:
                        details = json.loads(signal.raw_json) or {}
                    except Exception:
                        pass

                summary_lower = (signal.summary or "").lower()

                # Determine fyi_type
                if (
                    signal.signal_type in ("delivery_update", "shopping_order")
                    or signal.category == "shopping"
                    or any(x in summary_lower for x in ["delivered", "shipped", "out for delivery", "courier", "delivery"])
                ):
                    fyi_type = "delivery_notification"
                elif (
                    signal.signal_type == "school_update"
                    or signal.category == "education"
                    or any(x in summary_lower for x in ["school", "homework", "circular", "class"])
                ):
                    fyi_type = "school_circular"
                elif any(x in summary_lower for x in ["travel", "flight", "train", "booking", "ticket", "boarding"]):
                    fyi_type = "travel_update"
                elif (
                    signal.source == "whatsapp"
                    or signal.category == "personal"
                    or any(x in summary_lower for x in ["family", "spouse", "kids", "husband", "wife"])
                ):
                    fyi_type = "family_update"
                else:
                    fyi_type = "general_notification"

                # Extract content
                content = details.get("message_content") or details.get("summary") or signal.summary

                # Store FyiEvent
                fyi_obj = FyiEvent(
                    title=signal.summary,
                    fyi_type=fyi_type,
                    content=content,
                    source_signal_id=signal.id,
                    created_at=signal.created_at
                )
                db.add(fyi_obj)
                extracted_count += 1
                
                logger.debug(
                    f"Extracted FYI Event: '{fyi_obj.title}' "
                    f"| Type: {fyi_obj.fyi_type}"
                )

            db.commit()
            logger.success(f"Successfully extracted {extracted_count} FYI events.")
            return extracted_count

        except Exception as e:
            logger.exception(f"Error extracting FYI events: {e}")
            db.rollback()
            raise e
        finally:
            db.close()
