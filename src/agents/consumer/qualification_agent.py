import os
import json
import uuid
import re
from datetime import datetime, timezone

class SignalQualificationAgent:
    def __init__(self, config_dir: str = "config"):
        # Load configs
        with open(os.path.join(config_dir, "qualification_rules.json"), "r") as f:
            self.rules = json.load(f)
        with open(os.path.join(config_dir, "family_context.json"), "r") as f:
            self.family = json.load(f)
        with open(os.path.join(config_dir, "high_value_domains.json"), "r") as f:
            self.high_value = json.load(f)
        with open(os.path.join(config_dir, "jarvis_rules.json"), "r") as f:
            self.jarvis_rules = json.load(f)

    def qualify_signal(self, signal: dict, current_time: datetime = None) -> dict:
        if current_time is None:
            current_time = datetime.now(timezone.utc)
            
        message = signal.get("message", "") or ""
        msg_lower = message.lower()
        sender = (signal.get("sender") or "").lower()
        source = (signal.get("source") or "").lower()
        metadata = signal.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        
        # Parse timestamp
        mobile_timestamp_str = signal.get("mobile_timestamp")
        if isinstance(mobile_timestamp_str, str):
            try:
                # Handle various ISO timestamp strings
                val = mobile_timestamp_str.replace("Z", "+00:00")
                mobile_timestamp = datetime.fromisoformat(val)
            except Exception:
                mobile_timestamp = current_time
        elif isinstance(mobile_timestamp_str, datetime):
            mobile_timestamp = mobile_timestamp_str
        else:
            mobile_timestamp = current_time

        # --- V2 SOURCE-AWARE AUTOMATIC QUALIFICATION ---
        is_structured = False
        if source == "gpay" or source == "bank_statement":
            # Check GPay Contract
            if source == "gpay":
                has_amount = metadata.get("amount") is not None
                try:
                    amount_val = float(str(metadata.get("amount")).replace("$", "").replace(",", ""))
                except Exception:
                    amount_val = 0.0
                
                has_currency = metadata.get("currency") is not None
                has_counterparty = metadata.get("counterparty") is not None
                has_type = metadata.get("transaction_type") in ["DEBIT", "CREDIT"]
                
                if has_amount and amount_val > 0.0 and has_currency and has_counterparty and has_type:
                    is_structured = True
                    score = 100.0
                    status = "QUALIFIED"
                    reason = "gpay_structured_metadata"
                    amount = amount_val
                    currency = metadata.get("currency")
                    tx_type = metadata.get("transaction_type")
            
            # Check Bank Statement Contract
            elif source == "bank_statement":
                has_amount = metadata.get("amount") is not None
                try:
                    amount_val = float(str(metadata.get("amount")).replace("$", "").replace(",", ""))
                except Exception:
                    amount_val = 0.0
                
                has_currency = metadata.get("currency") is not None
                has_type = metadata.get("transaction_type") in ["DEBIT", "CREDIT"]
                has_ref_or_desc = (metadata.get("reference_number") is not None) or (metadata.get("description") is not None)
                
                if has_amount and amount_val > 0.0 and has_currency and has_type and has_ref_or_desc:
                    is_structured = True
                    score = 100.0
                    status = "QUALIFIED"
                    reason = "bank_statement_structured_metadata"
                    amount = amount_val
                    currency = metadata.get("currency")
                    tx_type = metadata.get("transaction_type")

        # If it is structured and met the contract, return immediately
        if is_structured:
            canonical = {
                "canonical_version": 1,
                "source_metadata": metadata,
                "qualification_info": {
                    "score": score,
                    "status": status,
                    "reason": reason,
                    "evaluated_at": current_time.isoformat()
                }
            }
            return {
                "score": score,
                "status": status,
                "reason": reason,
                "amount": amount,
                "currency": currency,
                "transaction_type": tx_type,
                "canonical_metadata": canonical
            }

        # --- UNSTRUCTURED/FALLBACK QUALIFICATION SCORING ENGINE ---

        # 1. Hard Reject Check
        # Age Filter (> 90 days)
        age_days = (current_time - mobile_timestamp).days
        if age_days > 90:
            return self._build_unstructured_response(0.0, "REJECTED", "stale_signal", signal, current_time)

        # WhatsApp pre-July exclusion rule
        if source == "whatsapp" and mobile_timestamp < datetime(2026, 7, 1, tzinfo=timezone.utc):
            return self._build_unstructured_response(0.0, "REJECTED", "excluded_pre_july_whatsapp", signal, current_time)

        # Badminton ignore
        if "badminton" in sender or "badminton" in msg_lower:
            return self._build_unstructured_response(0.0, "REJECTED", "badminton_ignore", signal, current_time)

        # Ignore topics from config
        ignore_topics = self.jarvis_rules.get("ignore_topics", [])
        if any(kw.lower() in msg_lower for kw in ignore_topics):
            return self._build_unstructured_response(0.0, "REJECTED", "ignore_topics", signal, current_time)

        # Conditional ignore topics from config
        conditional = self.jarvis_rules.get("conditional_ignore_topics", {})
        for topic, kws in conditional.items():
            if topic.lower() in msg_lower:
                if any(kw.lower() in msg_lower for kw in kws):
                    return self._build_unstructured_response(0.0, "REJECTED", "conditional_ignore_topics", signal, current_time)

        # OTP keyword rejection
        otp_keywords = ["otp", "verification code", "one-time password", "verification pin", "one time password", "your otp"]
        if any(kw in msg_lower for kw in otp_keywords):
            return self._build_unstructured_response(0.0, "REJECTED", "otp_message", signal, current_time)

        # WhatsApp system noise, reactions, calls, media placeholders
        wa_reaction_kws = ["reacted to", "reacted to your", "whatsapp reaction"]
        wa_call_kws = ["missed voice call", "missed video call", "incoming voice call", "incoming video call"]
        wa_media_kws = ["media omitted", "photo omitted", "video omitted", "audio omitted", "sticker omitted", "waiting for this message"]
        
        if any(kw in msg_lower for kw in wa_reaction_kws):
            return self._build_unstructured_response(0.0, "REJECTED", "whatsapp_reaction", signal, current_time)
            
        if source == "whatsapp" and any(kw in msg_lower for kw in wa_call_kws):
            return self._build_unstructured_response(0.0, "REJECTED", "whatsapp_call_status", signal, current_time)
            
        if source == "whatsapp" and any(kw in msg_lower for kw in wa_media_kws):
            return self._build_unstructured_response(0.0, "REJECTED", "whatsapp_media_placeholder", signal, current_time)

        # Telecom pack validity / data usage / hellotune / data loan
        telecom_kws = [
            "pack validity", "validity expired", "pack expired", "recharge your prepaid",
            "gb/day", "data pack", "data balance", "data usage", "data limit",
            "hellotune", "hello tune", "data loan",
            "about to expire", "expiring soon", "expiring tomorrow", "is expiring"
        ]
        if any(kw in msg_lower for kw in telecom_kws):
            return self._build_unstructured_response(0.0, "REJECTED", "telecom_alert", signal, current_time)
            
        # Promotional coupons / Marketing offers / Real-estate ads
        promo_kws = [
            "coupon", "promo coupon", "coupon code", "voucher",
            "marketing offer", "special offer", "discount", "sale is live",
            "real estate", "real-estate", "apartment for sale", "flat for sale",
            "plots for sale", "villa for sale", "plots in", "villa in", "apartments in",
            "3 bhk", "2 bhk"
        ]
        if any(kw in msg_lower for kw in promo_kws):
            return self._build_unstructured_response(0.0, "REJECTED", "promo_message", signal, current_time)

        # Credit card acquisition offer & Tighten Promotional Detection (Fix 2)
        acquisition_kws = [
            "apply now", "pre-approved", "guaranteed approval", "limited offer",
            "cashback offer", "lifetime free card", "lifetime free credit card",
            "no joining fee", "credit card offer", "card offer", "apply credit card",
            "apply for credit card"
        ]
        if any(kw in msg_lower for kw in acquisition_kws):
            return self._build_unstructured_response(0.0, "REJECTED", "promo_message", signal, current_time)

        # Financial ignore topics (from jarvis_rules.json)
        financial_ignore = self.jarvis_rules.get("financial_ignore", [])
        if any(kw.lower() in msg_lower for kw in financial_ignore):
            # Check if this is a true transaction before rejecting
            if not self._detect_financial_signal(message, msg_lower):
                return self._build_unstructured_response(0.0, "REJECTED", "financial_ignore", signal, current_time)

        # 2. Financial Signal Detection (Fix 3)
        financial_signal_detected = self._detect_financial_signal(message, msg_lower)

        # 3. Ambiguous Valuable Routing (Fix 4)
        is_ambiguous = False
        ambiguous_reason = None

        # Interest Credit
        if self._has_word(msg_lower, ["interest"]):
            is_ambiguous = True
            ambiguous_reason = "interest_credit"
            
        # Investment Activity
        elif self._has_word(msg_lower, ["mutual fund", "sip", "investment", "invested", "shares", "demat", "portfolio", "groww", "zerodha"]):
            is_ambiguous = True
            ambiguous_reason = "investment_activity"
            
        # Insurance Activity
        elif self._has_word(msg_lower, ["insurance", "premium", "policy", "lic", "hdfc ergo"]):
            is_ambiguous = True
            ambiguous_reason = "insurance_activity"
            
        # School Fee Alert
        elif self._has_word(msg_lower, ["school fee", "tuition fee", "admission fee", "school fees"]):
            is_ambiguous = True
            ambiguous_reason = "school_fee"
            
        # Medical Claim Alert
        elif self._has_word(msg_lower, ["medical claim", "insurance claim", "tpa", "claim approved", "hospitalization", "reimbursement claim"]):
            is_ambiguous = True
            ambiguous_reason = "medical_claim"
            
        # Unknown Merchant
        elif financial_signal_detected:
            known_entities = []
            
            # Trusted senders
            trusted_senders = self.rules.get("trusted_senders", [])
            known_entities.extend([ts.lower() for ts in trusted_senders])
            
            # Merchant categories
            merchants = self.jarvis_rules.get("merchant_categories", {})
            known_entities.extend([m.lower() for m in merchants.keys()])
            
            # High value domains
            for domain, kws in self.high_value.items():
                known_entities.extend([kw.lower() for kw in kws])
                
            # Family keywords
            family_kws = self.family.get("keywords", [])
            known_entities.extend([kw.lower() for kw in family_kws])
            
            matched_known = False
            for ent in known_entities:
                if ent in msg_lower or ent in sender:
                    matched_known = True
                    break
            
            if not matched_known:
                is_ambiguous = True
                ambiguous_reason = "unknown_merchant"

        # 4. Routing Decision Tree
        
        # If it is an ambiguous valuable signal, route to REVIEW
        if is_ambiguous:
            return self._build_unstructured_response(50.0, "REVIEW", ambiguous_reason or "review_needed", signal, current_time)

        # If it is a financial signal and NOT ambiguous, it is QUALIFIED
        if financial_signal_detected:
            return self._build_unstructured_response(95.0, "QUALIFIED", "financial_signal_detected", signal, current_time)

        # 5. Score Calculation for remaining signals (family/high value domain boosts)
        score = 40.0 # base score
        
        # Trusted Senders Qualification Override
        trusted_senders = self.rules.get("trusted_senders", [])
        if any(ts.lower() in sender for ts in trusted_senders):
            return self._build_unstructured_response(95.0, "QUALIFIED", "trusted_sender_qualification", signal, current_time)

        # Family context boost
        family_kws = self.family.get("keywords", [])
        if any(kw.lower() in msg_lower for kw in family_kws):
            score += self.rules.get("boosts", {}).get("family_context", 30)

        # High value domain boost
        matched_domain = False
        for domain, kws in self.high_value.items():
            if any(kw.lower() in msg_lower for kw in kws):
                matched_domain = True
                break
        if matched_domain:
            score += self.rules.get("boosts", {}).get("high_value_domain", 30)

        # High Confidence Valuable check
        if score >= 70.0:
            return self._build_unstructured_response(score, "QUALIFIED", "high_confidence_valuable", signal, current_time)
        
        # Everything Else goes to REJECTED
        return self._build_unstructured_response(score, "REJECTED", "low_score", signal, current_time)

    def _detect_financial_signal(self, message: str, msg_lower: str) -> bool:
        tx_keywords = [
            "spent", "spent on", "debited", "credited", "paid", "received", "txn", 
            "transaction", "salary", "interest", "upi", "imps", "neft",
            "credit card", "debit card", "card ending", "payment", "bank", 
            "bill", "invoice", "payable", "emi"
        ]
        has_tx_kw = any(kw in msg_lower for kw in tx_keywords)
        
        # Smart check for "due" (ignoring "due to" prepositions)
        if not has_tx_kw and "due" in msg_lower:
            if msg_lower.count("due") > msg_lower.count("due to"):
                has_tx_kw = True
                
        has_digits = any(c.isdigit() for c in message)
        return has_tx_kw and has_digits

    def _has_word(self, msg: str, words: list) -> bool:
        for w in words:
            pattern = r'\b' + re.escape(w) + r'\b'
            if re.search(pattern, msg):
                return True
        return False

    def _build_unstructured_response(self, score: float, status: str, reason: str, signal: dict, current_time: datetime) -> dict:
        metadata = signal.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}

        message = signal.get("message", "") or ""
        msg_lower = message.lower()

        # Try to extract financial details from metadata first
        amount = None
        currency = None
        tx_type = None
        
        if metadata.get("amount") is not None:
            try:
                amount = float(str(metadata.get("amount")).replace("$", "").replace(",", ""))
            except Exception:
                pass
        if metadata.get("currency") is not None:
            currency = metadata.get("currency")
        if metadata.get("transaction_type") in ["DEBIT", "CREDIT"]:
            tx_type = metadata.get("transaction_type")

        # Fallback to regex text parsing for unstructured financial messages
        is_financial = (status in ["QUALIFIED", "REVIEW"]) and any(kw in msg_lower for kw in ["spent", "paid", "debited", "credited", "received", "transaction", "txn"])
        
        if is_financial:
            if amount is None:
                # Try rs or inr regex
                amount_match = re.search(r"(?:rs\.?|inr)\s*([\d,]+(?:\.\d{2})?)", msg_lower)
                if amount_match:
                    try:
                        amount = float(amount_match.group(1).replace(",", ""))
                    except Exception:
                        pass
            if currency is None:
                currency = "INR"
            if tx_type is None:
                if any(kw in msg_lower for kw in ["credited", "received"]):
                    tx_type = "CREDIT"
                elif any(kw in msg_lower for kw in ["spent", "paid", "debited"]):
                    tx_type = "DEBIT"

        canonical = {
            "canonical_version": 1,
            "source_metadata": metadata,
            "qualification_info": {
                "score": score,
                "status": status,
                "reason": reason,
                "evaluated_at": current_time.isoformat()
            }
        }

        return {
            "score": score,
            "status": status,
            "reason": reason,
            "amount": amount,
            "currency": currency,
            "transaction_type": tx_type,
            "canonical_metadata": canonical
        }
