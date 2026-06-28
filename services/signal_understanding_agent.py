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
                    db.commit()
                    processed_count += 1
                except Exception as ex:
                    db.rollback()
                    logger.error(f"Error processing qualified signal ID {signal.id}: {ex}")

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
        # Error 1 fix: normalise whitespace before keyword matching.
        # HDFC IMPS credits arrive as "Received!\nINR 2,500.00" — the newline between
        # "Received!" and "INR" breaks a plain substring search for "received inr".
        # Collapsing all whitespace to a single space makes the match reliable.
        msg_normalised = re.sub(r'\s+', ' ', msg_lower).strip()
        sender_lower = signal.sender.lower()

        # 1. Financial transaction rule
        # Matches confirmed money movements: debits, credits, and received funds.
        # Uses msg_normalised so multi-line bank SMS formats are handled correctly.
        is_txn = any(kw in msg_normalised for kw in [
            "debited", "credited", "spent", "spent on", "card ending",
            "received rs", "received inr", "amount received", "amount credited",
            "transacted", "transaction of inr", "transaction of rs"
        ])
        if is_txn:
            # Extract currency and amount
            amount = None
            currency = "INR"
            amount_match = re.search(r"(?:rs\.?|inr)\s?([\d,]+(?:\.\d+)?)", msg_normalised)
            if amount_match:
                amount = float(amount_match.group(1).replace(",", ""))

            # Extract merchant/payee
            merchant = None
            merchant_match = re.search(
                r"(?:spent on|paid to|at|to)\s+([a-zA-Z0-9\s\.\-_%]+?)(?:\s+from|\s+via|\s+using|\.|\s*$)",
                msg_normalised
            )
            if merchant_match:
                merchant = merchant_match.group(1).strip()
            else:
                merchant = signal.sender

            # Error 7 fix: domain enrichment — if the payee is an insurance entity,
            # also emit the INSURANCE domain so the Financial Agent has full context.
            insurance_merchant_kws = ["insurance", "brokin", "lic", "hdfc life", "icici pru", "bajaj allianz", "policybazaar", "coverfox"]
            domains = ["FINANCE"]
            if any(kw in msg_normalised for kw in insurance_merchant_kws):
                domains.append("INSURANCE")

            # Set importance
            importance = "LOW"
            if "alert" in msg_normalised or "unauthorized" in msg_normalised:
                importance = "CRITICAL"

            return {
                "signal_id": signal.signal_id,
                "signal_type": "financial_transaction",
                "classes": ["FINANCIAL"],
                "domains": domains,
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

        # 2. Insurance rules — split into two sub-rules:
        #   2a. Insurance payment receipt (money already moved) → FINANCIAL + INFORMATION + ACTION
        #   2b. Insurance renewal/obligation reminder (money not moved) → INFORMATION + ACTION only
        insurance_kws = ["insurance", "renew", "renewal", "policy", "premium", "lic", "policybazaar"]
        if any(kw in msg_normalised for kw in insurance_kws):

            # Error 6 fix: Insurance payment receipt — money has already moved.
            # Pattern: insurer confirms they received payment ("received inr", "receipt no", "payment received").
            # Must fire BEFORE the renewal/obligation sub-rule to prevent misclassification.
            insurance_payment_receipt_kws = ["received inr", "received rs", "receipt no", "payment received", "payment of rs", "payment of inr"]
            if any(kw in msg_normalised for kw in insurance_payment_receipt_kws):
                ins_amount = None
                ins_amount_match = re.search(r"(?:rs\.?|inr)\s?([\d,]+(?:\.\d+)?)", msg_normalised)
                if ins_amount_match:
                    ins_amount = float(ins_amount_match.group(1).replace(",", ""))
                return {
                    "signal_id": signal.signal_id,
                    "signal_type": "general",
                    "classes": ["FINANCIAL", "INFORMATION", "ACTION"],
                    "domains": ["INSURANCE", "FINANCE"],
                    "importance": "HIGH",
                    "summary": f"Insurance payment receipt of INR {ins_amount or 'unknown'} from {signal.sender}",
                    "confidence": 1.0,
                    "reason": "Deterministic match: insurance payment receipt (money confirmed moved)",
                    "entities": {
                        "people": [],
                        "organizations": [signal.sender],
                        "merchants": [],
                        "monetary_value": {"amount": ins_amount, "currency": "INR"},
                        "deadlines": [],
                        "appointments": [],
                        "locations": [],
                        "travel_bookings": {},
                        "bills": {},
                        "insurance_policies": {"insurer": signal.sender},
                        "medical_events": {}
                    },
                    "routes": ["FinancialAgent", "TodoAgent", "FyiAgent"],
                    "raw_context": {
                        "source": signal.source,
                        "sender": signal.sender,
                        "timestamp": signal.timestamp.isoformat(),
                        "processing_path": "RULE_ENGINE",
                        "llm_model_used": "none"
                    }
                }

            # Error 5 fix: Insurance obligation reminder (renewal/due/expiry) — no money moved.
            # Require at least one genuine obligation keyword to emit ACTION class.
            # Policy document delivery notifications (no obligation keyword) fall through to LLM.
            obligation_kws = ["due", "renew", "expire", "expiry", "pay", "premium due", "last date"]
            if any(kw in msg_normalised for kw in obligation_kws):
                return {
                    "signal_id": signal.signal_id,
                    "signal_type": "general",
                    "classes": ["INFORMATION", "ACTION"],
                    "domains": ["INSURANCE"],
                    "importance": "HIGH",
                    "summary": f"Insurance renewal alert from {signal.sender}",
                    "confidence": 1.0,
                    "reason": "Deterministic match of insurance renewal obligation keywords",
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
                        "insurance_policies": {"insurer": signal.sender},
                        "medical_events": {}
                    },
                    # Insurance renewals are future obligations — FinancialAgent must not receive them
                    "routes": ["TodoAgent", "FyiAgent"],
                    "raw_context": {
                        "source": signal.source,
                        "sender": signal.sender,
                        "timestamp": signal.timestamp.isoformat(),
                        "processing_path": "RULE_ENGINE",
                        "llm_model_used": "none"
                    }
                }
            # Insurance keyword present but no obligation/payment — informational only (e.g. policy doc delivery)
            # Fall through to LLM for semantic handling

        # 3. Bill Reminder rule
        # Matches future payment obligations: bills due, outstanding amounts, credit card statements.
        # Error 3 fix: Exclude purchase receipts ("thank you for your purchase", "download your bill").
        # Those signals have money already moved and must be classified as FINANCIAL, not INFORMATION+ACTION.
        bill_kws = [
            "electricity bill", "tneb bill", "due date", "bill of", "pay before",
            "broadband bill", "utility bill", "bill alert", "card bill",
            "outstanding amount", "payment due", "minimum due", "total amount due"
        ]
        purchase_receipt_kws = [
            "thank you for your purchase", "download your bill", "purchase receipt",
            "your purchase at", "thanks for shopping"
        ]
        is_bill = any(kw in msg_normalised for kw in bill_kws) and any(kw in msg_normalised for kw in ["due", "outstanding", "pending", "pay"])
        is_purchase_receipt = any(kw in msg_normalised for kw in purchase_receipt_kws)
        if is_bill and not is_purchase_receipt:
            bill_amount = None
            bill_amount_match = re.search(r"(?:rs\.?|inr)\s?([\d,]+(?:\.\d+)?)", msg_normalised)
            if bill_amount_match:
                bill_amount = float(bill_amount_match.group(1).replace(",", ""))
            return {
                "signal_id": signal.signal_id,
                "signal_type": "general",
                "classes": ["INFORMATION", "ACTION", "ALERT"],
                "domains": ["FINANCE"],
                "importance": "HIGH",
                "summary": f"Bill payment reminder from {signal.sender}",
                "confidence": 1.0,
                "reason": "Deterministic match of bill payment keywords (future obligation)",
                "entities": {
                    "people": [],
                    "organizations": [signal.sender],
                    "merchants": [],
                    "monetary_value": {"amount": bill_amount, "currency": "INR"},
                    "deadlines": [],
                    "appointments": [],
                    "locations": [],
                    "travel_bookings": {},
                    "bills": {"provider": signal.sender},
                    "insurance_policies": {},
                    "medical_events": {}
                },
                # Bill due alerts are future obligations — FinancialAgent must not receive them
                "routes": ["TodoAgent", "FyiAgent"],
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
        # Refunds are confirmed money movements → FINANCIAL + INFORMATION.
        # Error 2 fix: Exclude future-tense refund promises ("will be refunded", "if debited will").
        # Those signals are failure/pending notifications — no money has moved yet.
        refund_kws = ["refund", "refunded", "reversed", "credited back", "reversal", "adjusted against"]
        future_refund_patterns = ["will be refunded", "will be reversed", "if debited will", "pending refund", "will refund"]
        if any(kw in msg_normalised for kw in refund_kws):
            # Guard: if the refund is conditional/future, it is INFORMATION+ALERT, not FINANCIAL
            if any(pat in msg_normalised for pat in future_refund_patterns):
                return {
                    "signal_id": signal.signal_id,
                    "signal_type": "general",
                    "classes": ["INFORMATION", "ALERT"],
                    "domains": ["FINANCE"],
                    "importance": "MEDIUM",
                    "summary": f"Payment failure notice from {signal.sender} — refund pending",
                    "confidence": 1.0,
                    "reason": "Future-tense refund detected: money not yet moved",
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
            # Confirmed refund — money has already moved
            refund_amount = None
            refund_currency = "INR"
            refund_amount_match = re.search(r"(?:rs\.?|inr)\s?([\d,]+(?:\.\d+)?)", msg_normalised)
            if refund_amount_match:
                refund_amount = float(refund_amount_match.group(1).replace(",", ""))
            return {
                "signal_id": signal.signal_id,
                "signal_type": "general",
                "classes": ["FINANCIAL", "INFORMATION"],
                "domains": ["FINANCE"],
                "importance": "MEDIUM",
                "summary": f"Refund of {refund_currency} {refund_amount or 'unknown'} from {signal.sender}",
                "confidence": 1.0,
                "reason": "Deterministic match of confirmed refund/reversal keywords",
                "entities": {
                    "people": [],
                    "organizations": [signal.sender],
                    "merchants": [],
                    "monetary_value": {"amount": refund_amount, "currency": refund_currency},
                    "deadlines": [],
                    "appointments": [],
                    "locations": [],
                    "travel_bookings": {},
                    "bills": {},
                    "insurance_policies": {},
                    "medical_events": {}
                },
                # FINANCIAL class → FinancialAgent receives the confirmed credit movement
                # INFORMATION class → FyiAgent records the notification for awareness
                "routes": ["FinancialAgent", "FyiAgent"],
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

CRITICAL FINANCIAL BOUNDARY RULES (never violate these):
- FINANCIAL class means money has ALREADY MOVED: a debit was confirmed, a credit was received, a payment completed, or a refund was processed.
- A bill due alert, outstanding balance notice, minimum payment reminder, or insurance premium reminder is NOT a FINANCIAL transaction — no money has moved yet. Use INFORMATION + ACTION + ALERT classes instead.
- Future payment obligations must NEVER emit FINANCIAL class.
- Refunds, reversed transactions, and credits that have already been processed DO emit FINANCIAL class.
- When in doubt about whether money has moved, do NOT emit FINANCIAL class.

Return ONLY valid JSON. No conversational notes or markdown formatting (no ```json).

Signal Details:
Source: {signal.source}
Sender: {signal.sender}
Message: {signal.message}

JSON Output:
"""
        try:
            logger.info("Invoking LLM for signal understanding...")
            try:
                response = self.router.ask(
                    prompt=prompt,
                    task_type=TaskType.EMAIL
                )
            except Exception as llm_err:
                logger.warning(f"LLM call failed, using deterministic fallback: {llm_err}")
                return {
                    "signal_type": "general",
                    "importance": "MEDIUM",
                    "classes": ["INFORMATION"],
                    "domains": ["GENERAL"],
                    "entities": {},
                    "summary": f"Informational alert from {signal.sender}",
                    "reason": signal.message,
                    "confidence": 0.85,
                    "raw_context": {
                        "processing_path": "FALLBACK_MOCK",
                        "llm_model_used": "fallback-model"
                    }
                }

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

    def _calculate_business_confidence(self, signal: QualifiedSignal, contract: dict, processing_path: str) -> float:
        """
        Calculates a hybrid business confidence score.

        Business confidence reflects how safe it is to auto-process this signal without human review.
        It differs from raw LLM confidence (which is model-internal) by accounting for:
          - Source reliability (trusted bank senders vs. unknown numbers)
          - Entity completeness (FINANCIAL class but no amount extracted = lower confidence)
          - Parse quality (LLM output had low raw confidence)

        Thresholds (per semantic_alignment_report.md):
          >= 0.85 → Auto-process
          0.50–0.84 → Route but flag requires_review = true
          < 0.50 → Critical Inbox (no downstream routing until user reviews)
        """
        # Base confidence: deterministic rules are fully trusted; LLM uses its reported confidence
        if processing_path == "RULE_ENGINE":
            base = 1.0
        else:
            # LLM may return "confidence": null — use `or 0.8` to handle both None and missing key
            base = float(contract.get("confidence") or 0.8)

        # ── Source Reliability Modifier ───────────────────────────────────────
        # Trusted bank / institutional senders get a small boost
        trusted_sender_fragments = [
            "hdfcbk", "sbipsg", "sbicrd", "icicibk", "kotakbk", "axisbk",
            "licind", "irctc", "paytm", "phonepe", "amazonpay"
        ]
        sender_lower = signal.sender.lower()
        if any(frag in sender_lower for frag in trusted_sender_fragments):
            base = min(1.0, base + 0.05)
        elif signal.source == "whatsapp" and sender_lower.replace(" ", "").replace("+", "").isdigit():
            # Unknown numeric WhatsApp sender — reduce confidence slightly
            base = max(0.0, base - 0.10)

        # ── Entity Completeness Check ─────────────────────────────────────────
        # If FINANCIAL class is present but no monetary amount was extracted,
        # the understanding is incomplete — reduce confidence significantly
        classes = contract.get("classes", [])
        if "FINANCIAL" in classes:
            entities = contract.get("entities", {})
            monetary = entities.get("monetary_value", {})
            if not monetary or monetary.get("amount") is None:
                base = max(0.0, base - 0.30)

        # ── Parse Quality Penalty (LLM path only) ────────────────────────────
        # If the LLM returned a low raw confidence, compound the penalty
        if processing_path == "LLM":
            raw_llm_confidence = float(contract.get("confidence") or 0.8)
            if raw_llm_confidence < 0.75:
                base = max(0.0, base - 0.15)

        return round(base, 4)
