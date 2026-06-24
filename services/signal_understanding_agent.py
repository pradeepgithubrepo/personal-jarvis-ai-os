# services/signal_understanding_agent.py

import json
import re
import uuid
from datetime import datetime
from loguru import logger

from configs.settings import settings
from configs.constants import TaskType
from intelligence.routing.router import IntelligenceRouter
from storage.db.database import SessionLocal
from storage.models.qualified_signal import QualifiedSignal
from storage.models.understood_signal import UnderstoodSignal
from services.supabase_repo import SupabaseRepo


class SignalUnderstandingAgent:
    """
    Decoupled LLM-powered Understanding layer.
    Processes qualified signals and produces the canonical understanding contract.
    """

    def __init__(self):
        self.router = IntelligenceRouter()
        self.llm_model = getattr(settings, "local_model", "qwen3:1.7b")

    def run_shadow_mode(self):
        """
        Runs the shadow understanding pipeline.
        Fetches qualified signals, processes them using the new understanding logic,
        and persists them into the understood_signals table.
        """
        logger.info("Running Signal Understanding Agent in Shadow Mode...")
        db = SessionLocal()
        try:
            # Get all qualified signals
            qualified_signals = db.query(QualifiedSignal).filter(
                QualifiedSignal.qualification_status == "QUALIFIED"
            ).all()

            # Find already processed qualified signals to avoid duplication
            already_understood = {
                int(row[0]) for row in db.query(UnderstoodSignal.qualified_signal_id).all()
            }

            unprocessed = [s for s in qualified_signals if s.id not in already_understood]
            logger.info(f"Found {len(unprocessed)} unprocessed qualified signals for understanding.")

            processed_count = 0
            for signal in unprocessed:
                try:
                    self.process_signal(signal, db)
                    processed_count += 1
                except Exception as ex:
                    logger.error(f"Error processing qualified signal ID {signal.id}: {ex}")

            db.commit()
            logger.success(f"Signal Understanding shadow run complete. Processed {processed_count} signals.")
            return processed_count
        except Exception as e:
            logger.error(f"Error in running understanding agent shadow mode: {e}")
            db.rollback()
            raise e
        finally:
            db.close()

    def process_signal(self, signal: QualifiedSignal, db) -> dict:
        """
        Processes a single qualified signal, persists it to DBs, and returns the contract.
        """
        logger.info(f"Understanding qualified signal ID {signal.id} (Sender: {signal.sender})")
        
        # 1. Deterministic path
        contract = self._try_deterministic_path(signal)
        
        # 2. Fallback to LLM path if deterministic is None
        if contract is None:
            contract = self._run_llm_path(signal)

        # Generate unique UUID for understood_signal
        understood_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"understood-{signal.id}"))
        
        # Determine paths
        processing_path = contract["raw_context"].get("processing_path", "LLM")
        llm_model_used = contract["raw_context"].get("llm_model_used", self.llm_model)

        # Check confidence dynamically using the Business Confidence Model
        confidence_val = self._calculate_business_confidence(signal, contract, processing_path)

        contract["confidence"] = confidence_val
        is_verified = confidence_val >= 0.85

        # Store to SQLite
        db_obj = UnderstoodSignal(
            id=understood_id,
            qualified_signal_id=signal.id,
            raw_signal_id=signal.signal_id,
            signal_type=contract["signal_type"],
            importance=contract["importance"],
            confidence=contract["confidence"],
            summary=contract["summary"],
            reason=contract["reason"],
            processing_path=processing_path,
            llm_model_used=llm_model_used,
            contract_json=json.dumps(contract),
            is_verified=is_verified,
            created_at=signal.timestamp
        )
        db.add(db_obj)

        # Store to remote Supabase (fails gracefully if port blocked)
        try:
            SupabaseRepo.save_understood_signal(
                understood_id=uuid.UUID(understood_id),
                qualified_signal_id=signal.id,
                raw_signal_id=signal.signal_id,
                signal_type=contract["signal_type"],
                importance=contract["importance"],
                confidence=contract["confidence"],
                summary=contract["summary"],
                reason=contract["reason"],
                processing_path=processing_path,
                llm_model_used=llm_model_used,
                contract_json=contract,
                is_verified=is_verified,
                created_at=signal.timestamp
            )
        except Exception as e:
            logger.warning(f"Failed to save understood signal to remote Supabase: {e}")

        logger.info(f"Saved understood signal {understood_id} via {processing_path} path.")
        return contract

    def _try_deterministic_path(self, signal: QualifiedSignal) -> dict | None:
        """
        Regex & keyword-based parsing rules matching specific signal types.
        """
        msg_lower = signal.message.lower()
        sender_lower = signal.sender.lower()

        # 1. Financial transaction rule
        # Check spending/credits or direct transaction signals
        is_txn = any(kw in msg_lower for kw in ["debited", "credited", "spent", "spent on", "card ending", "received rs", "transacted"])
        if is_txn:
            # Extract currency and amount
            amount = None
            currency = "INR"
            amount_match = re.search(r"(?:rs\.?|inr)\s?([\d,]+(?:\.\d+)?)", msg_lower)
            if amount_match:
                amount = float(amount_match.group(1).replace(",", ""))

            # Extract merchant/payee
            merchant = None
            merchant_match = re.search(r"(?:spent on|paid to|at)\s+([a-zA-Z0-9\s\.\-_%]+?)(?:\s+from|\s+via|\s+using|\.|\s*$)", msg_lower)
            if merchant_match:
                merchant = merchant_match.group(1).strip()
            else:
                merchant = signal.sender

            # Set importance
            importance = "LOW"
            if "alert" in msg_lower or "unauthorized" in msg_lower:
                importance = "CRITICAL"

            return {
                "signal_id": signal.signal_id,
                "signal_type": "financial_transaction",
                "classes": ["FINANCIAL"],
                "domains": ["FINANCE"],
                "importance": importance,
                "summary": f"Transaction of {currency} {amount or 'unknown'} at {merchant or 'merchant'}",
                "confidence": 1.0,
                "reason": "Deterministic match of financial transaction keywords",
                "entities": {
                    "people": [],
                    "organizations": [signal.sender],
                    "merchants": [merchant] if merchant else [],
                    "monetary_value": {
                        "amount": amount,
                        "currency": currency
                    },
                    "deadlines": [],
                    "appointments": [],
                    "locations": [],
                    "travel_bookings": {},
                    "bills": {},
                    "insurance_policies": {},
                    "medical_events": {}
                },
                "routes": ["FinancialAgent"],
                "raw_context": {
                    "source": signal.source,
                    "sender": signal.sender,
                    "timestamp": signal.timestamp.isoformat(),
                    "processing_path": "RULE_ENGINE",
                    "llm_model_used": "none"
                }
            }

        # 2. Insurance Renewal rule
        insurance_kws = ["insurance", "renew", "renewal", "policy", "premium", "lic", "policybazaar"]
        if any(kw in msg_lower for kw in insurance_kws) and any(kw in msg_lower for kw in ["due", "renew", "expire", "expiry"]):
            return {
                "signal_id": signal.signal_id,
                "signal_type": "general",
                "classes": ["INFORMATION", "ACTION"],
                "domains": ["INSURANCE"],
                "importance": "HIGH",
                "summary": f"Insurance renewal alert from {signal.sender}",
                "confidence": 1.0,
                "reason": "Deterministic match of insurance renewal keywords",
                "entities": {
                    "people": [],
                    "organizations": [signal.sender],
                    "merchants": [],
                    "monetary_value": {
                        "amount": None,
                        "currency": "INR"
                    },
                    "deadlines": [],
                    "appointments": [],
                    "locations": [],
                    "travel_bookings": {},
                    "bills": {},
                    "insurance_policies": {
                        "insurer": signal.sender
                    },
                    "medical_events": {}
                },
                "routes": ["FinancialAgent", "TodoAgent"],
                "raw_context": {
                    "source": signal.source,
                    "sender": signal.sender,
                    "timestamp": signal.timestamp.isoformat(),
                    "processing_path": "RULE_ENGINE",
                    "llm_model_used": "none"
                }
            }

        # 3. Bill Reminder rule
        bill_kws = ["electricity bill", "tneb bill", "due date", "bill of", "pay before", "broadband bill", "utility bill"]
        if any(kw in msg_lower for kw in bill_kws) and any(kw in msg_lower for kw in ["due", "outstanding", "pending", "pay"]):
            return {
                "signal_id": signal.signal_id,
                "signal_type": "general",
                "classes": ["INFORMATION", "ACTION", "ALERT"],
                "domains": ["FINANCE"],
                "importance": "HIGH",
                "summary": f"Utility bill payment reminder from {signal.sender}",
                "confidence": 1.0,
                "reason": "Deterministic match of bill payment keywords",
                "entities": {
                    "people": [],
                    "organizations": [signal.sender],
                    "merchants": [],
                    "monetary_value": {
                        "amount": None,
                        "currency": "INR"
                    },
                    "deadlines": [],
                    "appointments": [],
                    "locations": [],
                    "travel_bookings": {},
                    "bills": {
                        "provider": signal.sender
                    },
                    "insurance_policies": {},
                    "medical_events": {}
                },
                "routes": ["FinancialAgent", "TodoAgent"],
                "raw_context": {
                    "source": signal.source,
                    "sender": signal.sender,
                    "timestamp": signal.timestamp.isoformat(),
                    "processing_path": "RULE_ENGINE",
                    "llm_model_used": "none"
                }
            }

        # 4. Travel Booking rule
        travel_kws = ["booking", "pnr", "ticket", "flight", "train", "irctc", "boarding"]
        if any(kw in msg_lower for kw in travel_kws) and any(kw in msg_lower for kw in ["confirmed", "booked", "seat", "pnr"]):
            return {
                "signal_id": signal.signal_id,
                "signal_type": "travel_booking",
                "classes": ["INFORMATION"],
                "domains": ["TRAVEL"],
                "importance": "MEDIUM",
                "summary": f"Travel booking confirmation from {signal.sender}",
                "confidence": 1.0,
                "reason": "Deterministic match of travel booking keywords",
                "entities": {
                    "people": [],
                    "organizations": [signal.sender],
                    "merchants": [],
                    "monetary_value": {
                        "amount": None,
                        "currency": "INR"
                    },
                    "deadlines": [],
                    "appointments": [],
                    "locations": [],
                    "travel_bookings": {
                        "carrier": signal.sender
                    },
                    "bills": {},
                    "insurance_policies": {},
                    "medical_events": {}
                },
                "routes": ["FyiAgent"],
                "raw_context": {
                    "source": signal.source,
                    "sender": signal.sender,
                    "timestamp": signal.timestamp.isoformat(),
                    "processing_path": "RULE_ENGINE",
                    "llm_model_used": "none"
                }
            }

        # 5. Delivery Update rule
        delivery_kws = ["delivered", "out for delivery", "courier dispatch", "amazon order", "flipkart order", "delivery partner"]
        if any(kw in msg_lower for kw in delivery_kws):
            return {
                "signal_id": signal.signal_id,
                "signal_type": "delivery_update",
                "classes": ["INFORMATION"],
                "domains": ["TRAVEL"],
                "importance": "MEDIUM",
                "summary": f"Delivery update from {signal.sender}",
                "confidence": 1.0,
                "reason": "Deterministic match of delivery status keywords",
                "entities": {
                    "people": [],
                    "organizations": [signal.sender],
                    "merchants": [],
                    "monetary_value": {
                        "amount": None,
                        "currency": "INR"
                    },
                    "deadlines": [],
                    "appointments": [],
                    "locations": [],
                    "travel_bookings": {},
                    "bills": {},
                    "insurance_policies": {},
                    "medical_events": {}
                },
                "routes": ["FyiAgent"],
                "raw_context": {
                    "source": signal.source,
                    "sender": signal.sender,
                    "timestamp": signal.timestamp.isoformat(),
                    "processing_path": "RULE_ENGINE",
                    "llm_model_used": "none"
                }
            }

        # 6. Refund rule
        if "refund" in msg_lower:
            return {
                "signal_id": signal.signal_id,
                "signal_type": "general",
                "classes": ["FINANCIAL", "INFORMATION"],
                "domains": ["FINANCE"],
                "importance": "MEDIUM",
                "summary": f"Refund notification from {signal.sender}",
                "confidence": 1.0,
                "reason": "Deterministic match of refund keyword",
                "entities": {
                    "people": [],
                    "organizations": [signal.sender],
                    "merchants": [],
                    "monetary_value": {"amount": None, "currency": "INR"},
                    "deadlines": [],
                    "appointments": [],
                    "locations": [],
                    "travel_bookings": {},
                    "bills": {},
                    "insurance_policies": {},
                    "medical_events": {}
                },
                "routes": ["FyiAgent"],
                "raw_context": {
                    "source": signal.source,
                    "sender": signal.sender,
                    "timestamp": signal.timestamp.isoformat(),
                    "processing_path": "RULE_ENGINE",
                    "llm_model_used": "none"
                }
            }

        # 7. Medical appointment rule
        appointment_kws = ["appointment", "doctor", "clinic", "visit", "checkup"]
        if any(kw in msg_lower for kw in appointment_kws):
            return {
                "signal_id": signal.signal_id,
                "signal_type": "general",
                "classes": ["INFORMATION", "ACTION"],
                "domains": ["MEDICAL"],
                "importance": "MEDIUM",
                "summary": f"Medical appointment notification from {signal.sender}",
                "confidence": 1.0,
                "reason": "Deterministic match of medical appointment keywords",
                "entities": {
                    "people": [],
                    "organizations": [signal.sender],
                    "merchants": [],
                    "monetary_value": {"amount": None, "currency": "INR"},
                    "deadlines": [],
                    "appointments": [],
                    "locations": [],
                    "travel_bookings": {},
                    "bills": {},
                    "insurance_policies": {},
                    "medical_events": {}
                },
                "routes": ["TodoAgent"],
                "raw_context": {
                    "source": signal.source,
                    "sender": signal.sender,
                    "timestamp": signal.timestamp.isoformat(),
                    "processing_path": "RULE_ENGINE",
                    "llm_model_used": "none"
                }
            }

        return None

    def _run_llm_path(self, signal: QualifiedSignal) -> dict:
        """
        Invokes LLM fallback path to construct semantic understanding payload.
        """
        prompt = f"""
You are a mobile notification and email understanding agent.
Your goal is to parse the qualified incoming signal and output a valid JSON contract.

Field specifications:
1. "signal_type": strictly one of: "school_update", "financial_transaction", "delivery_update", "travel_booking", "general".
2. "classes": a list containing any of: "ACTION", "FINANCIAL", "INFORMATION", "MEMORY", "ALERT".
3. "domains": a list containing any of: "FAMILY", "FINANCE", "INSURANCE", "MEDICAL", "TRAVEL", "WORK", "EDUCATION", "GENERAL".
4. "importance": strictly one of: "CRITICAL", "HIGH", "MEDIUM", "LOW", "IGNORE".
5. "summary": a short synthetic summary of the message context.
6. "confidence": float value between 0.0 and 1.0 reflecting classification confidence.
7. "reason": fyi reasoning why this was classified so.
8. "entities": a JSON object with:
    - "people": list of strings or []
    - "organizations": list of strings or []
    - "merchants": list of strings or []
    - "monetary_value": {{ "amount": float/null, "currency": "INR"/"USD"/null }}
    - "deadlines": list of dates "YYYY-MM-DD" or []
    - "appointments": list of datetimes "YYYY-MM-DDTHH:MM:SSZ" or []
    - "locations": list of strings or []
    - "travel_bookings": object or {{}}
    - "bills": object or {{}}
    - "insurance_policies": object or {{}}
    - "medical_events": object or {{}}

Rules:
- If domain is EDUCATION / School Circular: classes must include INFORMATION, ACTION, or MEMORY.
- If signal relates to family parenting / spouse: domain must include FAMILY.
- If debit/credit or payment transaction: classes must include FINANCIAL.

Return ONLY valid JSON. No conversational notes or markdown formatting (no ```json).

Signal Details:
Source: {signal.source}
Sender: {signal.sender}
Message: {signal.message}

JSON Output:
"""
        try:
            logger.info("Invoking LLM for signal understanding...")
            response = self.router.ask(
                prompt=prompt,
                task_type=TaskType.EMAIL
            )

            cleaned = (
                response
                .replace("```json", "")
                .replace("```", "")
                .strip()
            )

            start_idx = cleaned.find("{")
            end_idx = cleaned.rfind("}")
            if start_idx != -1 and end_idx != -1:
                cleaned = cleaned[start_idx:end_idx + 1]

            result = json.loads(cleaned)

            # Defensive corrections
            if "signal_type" not in result:
                result["signal_type"] = "general"
            if "classes" not in result or not isinstance(result["classes"], list):
                result["classes"] = ["INFORMATION"]
            if "domains" not in result or not isinstance(result["domains"], list):
                result["domains"] = ["GENERAL"]
            if "importance" not in result:
                result["importance"] = "MEDIUM"
            if "summary" not in result or not result["summary"]:
                result["summary"] = signal.message[:100]
            if "confidence" not in result:
                result["confidence"] = 0.8
            if "reason" not in result:
                result["reason"] = "LLM classification fallback"
            if "entities" not in result or not isinstance(result["entities"], dict):
                result["entities"] = {}

            # Map routes based on classes
            routes = []
            classes_set = set(result["classes"])
            if "FINANCIAL" in classes_set:
                routes.append("FinancialAgent")
            if "ACTION" in classes_set:
                routes.append("TodoAgent")
            if "INFORMATION" in classes_set:
                routes.append("FyiAgent")
            if "MEMORY" in classes_set:
                routes.append("FactAgent")
            result["routes"] = routes

            result["signal_id"] = signal.signal_id
            result["raw_context"] = {
                "source": signal.source,
                "sender": signal.sender,
                "timestamp": signal.timestamp.isoformat(),
                "processing_path": "LLM",
                "llm_model_used": self.llm_model
            }

            return result

        except Exception as e:
            logger.warning(f"LLM Parsing failed for qualified signal {signal.id}: {e}. Generating default contract.")
            return {
                "signal_id": signal.signal_id,
                "signal_type": "general",
                "classes": ["INFORMATION"],
                "domains": ["GENERAL"],
                "importance": "MEDIUM",
                "summary": signal.message[:100],
                "confidence": 0.5,
                "reason": f"Fallback due to LLM error: {e}",
                "entities": {},
                "routes": ["FyiAgent"],
                "raw_context": {
                    "source": signal.source,
                    "sender": signal.sender,
                    "timestamp": signal.timestamp.isoformat(),
                    "processing_path": "LLM",
                    "llm_model_used": self.llm_model
                }
            }
