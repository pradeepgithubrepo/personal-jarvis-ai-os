import json
import re
from datetime import datetime, timezone
from loguru import logger
from configs.settings import settings
from intelligence.llm_client import LLMClient

def extract_entities(message: str) -> list[str]:
    # Match capitalized words and acronyms (like SBI, HDFC)
    candidates = re.findall(r"\b[A-Z][a-zA-Z0-9]+\b", message)
    exclude = {"Alert", "Your", "Dear", "Customer", "Bank", "Info", "Txn", "Use", "This", "The", "And", "With", "For", "Rs", "Inr", "Good", "Morning", "Have", "A", "Is", "Note"}
    entities = list(set([c for c in candidates if c not in exclude]))
    return entities

class SignalUnderstandingAgent:
    def __init__(self, client=None, model_name: str = None, provider: str = None):
        self.client = client
        self.model = model_name or settings.local_model or "qwen2.5:1.5b"
        self.provider = provider or settings.model_provider or "local"
        self.llm_client = LLMClient(provider=self.provider, model=self.model)

    def understand_signal(self, signal: dict) -> dict:
        """
        Processes a qualified signal to classify it and extract contract information.
        Returns a dict mapped to the understood_signals table.
        """
        message = signal.get("message", "")
        msg_lower = message.lower()
        sender = signal.get("sender", "")
        source = signal.get("source", "")
        timestamp = signal.get("timestamp")
        metadata = signal.get("metadata") or {}
        
        # --- V2 METADATA-FIRST BYPASS FOR STRUCTURED SIGNALS ---
        if source in ["gpay", "bank_statement"]:
            # Check physical columns or metadata blocks
            amount = signal.get("amount")
            currency = signal.get("currency")
            tx_type = signal.get("transaction_type")
            
            source_meta = metadata.get("source_metadata") or {}
            if amount is None:
                amount = source_meta.get("amount")
            if currency is None:
                currency = source_meta.get("currency")
            if tx_type is None:
                tx_type = source_meta.get("transaction_type")
                
            try:
                if amount is not None:
                    amount = float(str(amount).replace("$", "").replace(",", ""))
            except Exception:
                amount = None
                
            if amount is not None and currency and tx_type:
                # We have a valid structured transaction! Bypass LLM!
                merchant = source_meta.get("counterparty") or source_meta.get("receiver") or sender
                contract = {
                    "amount": amount,
                    "currency": currency,
                    "transaction_type": tx_type,
                    "payment_channel": source_meta.get("payment_channel") or "UPI",
                    "merchant": merchant
                }
                
                summary = f"Paid {amount} {currency} to {merchant}." if tx_type == "DEBIT" else f"Received {amount} {currency} from {merchant}."
                
                result = {
                    "signal_type": "FINANCIAL",
                    "importance": 0.9,
                    "confidence": 1.0,
                    "summary": summary,
                    "reason": f"Structured {source} metadata bypass",
                    "processing_path": "metadata_bypass",
                    "llm_model_used": None,
                    "contract_json": contract,
                    "metadata": {
                        "processing_path": "metadata_bypass",
                        "llm_model_used": None,
                        "escalation_reason": "",
                    }
                }
                return self._normalize_contract_fields(result, message, sender)
        
        # 1. Deterministic override for NOISE classification (Greetings, OTPs, promotional spam)
        noise_keywords = ["otp", "verification code", "one-time password", "verification pin", "one time password", "trans.no", "your otp"]
        greeting_keywords = ["good morning", "good night", "happy birthday", "have a wonderful day", "have a great day"]
        promo_keywords = ["vi.in", "recharge your prepaid", "gb/day", "promo code", "discount", "click to buy"]
        
        is_noise = (
            any(kw in msg_lower for kw in noise_keywords) or
            any(kw in msg_lower for kw in greeting_keywords) or
            any(kw in msg_lower for kw in promo_keywords)
        )
        
        if is_noise:
            result = {
                "signal_type": "NOISE",
                "importance": 0.1,
                "confidence": 1.0,
                "summary": message[:100] + "..." if len(message) > 100 else message,
                "reason": "Deterministic noise classification (OTP/greetings/spam)",
                "processing_path": "fallback",
                "llm_model_used": None,
                "contract_json": {},
                "metadata": {
                    "processing_path": "fallback",
                    "llm_model_used": None,
                    "escalation_reason": "",
                }
            }
            return self._normalize_contract_fields(result, message, sender)

        # 2. LLM classification path
        prompt = self._build_prompt(message, sender, source, timestamp)
        
        import time
        start_time = time.time()
        
        res = None
        path = None
        model_used = None
        escalation_reason = ""
        
        # --- TIER 1: Cerebras ---
        try:
            raw_response = self.llm_client.ask(prompt, provider="cerebras", model="gemma-4-31b")
            parsed = self._parse_llm_response(raw_response)
            if parsed:
                res = parsed
                path = "CEREBRAS_DIRECT"
                model_used = "gemma-4-31b"
            else:
                escalation_reason = "Cerebras returned invalid JSON/schema"
        except Exception as e:
            escalation_reason = f"Cerebras exception: {str(e)}"
            
        # Check Cerebras escalation conditions (Tier 1 -> Tier 2)
        escalate_to_groq = False
        if res is None:
            escalate_to_groq = True
        elif res.get("confidence", 0.0) < 0.85:
            escalate_to_groq = True
            escalation_reason = f"Cerebras confidence too low ({res.get('confidence')})"
        elif res.get("signal_type") == "FINANCIAL" and not res.get("contract_json", {}).get("amount"):
            escalate_to_groq = True
            escalation_reason = "Cerebras FINANCIAL contract missing amount"
        elif res.get("signal_type") == "ACTION" and not res.get("contract_json", {}).get("task_name"):
            escalate_to_groq = True
            escalation_reason = "Cerebras ACTION contract missing task_name"
            
        # --- TIER 2: Groq ---
        if escalate_to_groq:
            logger.info(f"Escalating to Groq. Reason: {escalation_reason}")
            try:
                raw_response = self.llm_client.ask(prompt, provider="groq", model="llama-3.1-8b-instant")
                parsed = self._parse_llm_response(raw_response)
                if parsed:
                    res = parsed
                    path = "CEREBRAS_TO_GROQ"
                    model_used = "llama-3.1-8b-instant"
                else:
                    escalation_reason = "Groq returned invalid JSON/schema"
            except Exception as e:
                escalation_reason = f"Groq exception: {str(e)}"
                
            # Check Groq escalation conditions (Tier 2 -> Tier 3)
            escalate_to_gemini = False
            if res is None:
                escalate_to_gemini = True
            elif res.get("confidence", 0.0) < 0.60:
                res = None
                escalate_to_gemini = True
                escalation_reason = f"Groq confidence too low ({res.get('confidence')})"
                
            # --- TIER 3: Gemini ---
            if escalate_to_gemini:
                logger.info(f"Escalating to Gemini. Reason: {escalation_reason}")
                try:
                    raw_response = self.llm_client.ask(prompt, provider="gemini", model="gemini-2.5-flash")
                    parsed = self._parse_llm_response(raw_response)
                    if parsed:
                        res = parsed
                        path = "CEREBRAS_TO_GROQ_TO_GEMINI"
                        model_used = "gemini-2.5-flash"
                    else:
                        escalation_reason = "Gemini returned invalid JSON/schema"
                except Exception as e:
                    escalation_reason = f"Gemini exception: {str(e)}"
                    
                # Check Gemini escalation conditions (Tier 3 -> Tier 4)
                escalate_to_mistral = False
                if res is None:
                    escalate_to_mistral = True
                    
                # --- TIER 4: Mistral ---
                if escalate_to_mistral:
                    logger.info(f"Escalating to Mistral. Reason: {escalation_reason}")
                    try:
                        raw_response = self.llm_client.ask(prompt, provider="mistral", model="mistral-small-latest")
                        parsed = self._parse_llm_response(raw_response)
                        if parsed:
                            res = parsed
                            path = "CEREBRAS_TO_GROQ_TO_GEMINI_TO_MISTRAL"
                            model_used = "mistral-small-latest"
                        else:
                            escalation_reason = "Mistral returned invalid JSON/schema"
                    except Exception as e:
                        escalation_reason = f"Mistral exception: {str(e)}"
                        
                    # Check Mistral escalation conditions (Tier 4 -> Tier 5)
                    escalate_to_qwen = False
                    if res is None:
                        escalate_to_qwen = True
                        
                    # --- TIER 5: Local Qwen ---
                    if escalate_to_qwen:
                        logger.info(f"Escalating to Local Qwen. Reason: {escalation_reason}")
                        try:
                            raw_response = self.llm_client.ask(prompt, provider="local", model="qwen2.5:1.5b")
                            parsed = self._parse_llm_response(raw_response)
                            if parsed:
                                res = parsed
                                path = "CEREBRAS_TO_GROQ_TO_GEMINI_TO_MISTRAL_TO_QWEN"
                                model_used = "qwen2.5:1.5b"
                            else:
                                escalation_reason = "Local Qwen returned invalid JSON/schema"
                        except Exception as e:
                            escalation_reason = f"Local Qwen exception: {str(e)}"
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        if res:
            res["processing_path"] = path
            res["llm_model_used"] = model_used
            res["metadata"] = {
                "processing_path": path,
                "llm_model_used": model_used,
                "escalation_reason": escalation_reason if path != "CEREBRAS_DIRECT" else "",
                "processing_duration_ms": duration_ms
            }
            return self._normalize_contract_fields(res, message, sender)
            
        # 3. Fallback heuristics
        fallback_res = self._fallback_understand(signal)
        fallback_res["metadata"] = {
            "processing_path": "fallback",
            "llm_model_used": None,
            "escalation_reason": f"All LLM tiers failed. Last reason: {escalation_reason}",
            "processing_duration_ms": duration_ms
        }
        return self._normalize_contract_fields(fallback_res, message, sender)

    def _normalize_contract_fields(self, result: dict, message: str, sender: str = "") -> dict:
        """
        Appends canonical fields to contract_json programmatically.
        """
        # Apply the SUA Action Override before normalization
        result = self._apply_action_override(result, message, sender)

        contract = result.get("contract_json", {})
        if not isinstance(contract, dict):
            contract = {}
            
        sig_type = result.get("signal_type")
        
        # Inject standard canonical contract fields
        contract["entities"] = extract_entities(message)
        contract["financial_candidate"] = (sig_type == "FINANCIAL")
        contract["fact_candidate"] = False
        contract["fyi_candidate"] = (sig_type == "FYI")
        contract["noise_candidate"] = (sig_type == "NOISE")
        contract["requires_action"] = (sig_type == "ACTION")
        contract["memory_candidate"] = (sig_type in ["ACTION", "FYI"])
        
        result["contract_json"] = contract
        return result

    def _apply_action_override(self, result: dict, message: str, sender: str) -> dict:
        msg_lower = message.lower()
        sender_lower = (sender or "").lower()
        
        # Check if the message is currently FYI or NOISE
        current_type = result.get("signal_type")
        if current_type not in ["FYI", "NOISE"]:
            return result
            
        # 1. Action/Obligation keywords lists
        # Strong Action Verbs: typically require a deadline to override generally,
        # but override immediately in sensitive domains.
        strong_action_verbs = [
            "submit", "pay", "upload", "renew", "verify", "register", "complete", "sign"
        ]
        weak_action_verbs = [
            "bring", "attend", "join", "provide", "carry", "wear", "request", "require", 
            "compulsory", "mandatory", "must", "please", "kindly", "feedback", "fill", "update"
        ]
        all_action_verbs = strong_action_verbs + weak_action_verbs
        
        # Deadlines / Time indicators
        strong_deadlines = [
            "tomorrow", "deadline", "due date", "last date", "on or before", "before"
        ]
        weak_deadlines = [
            "by monday", "by tuesday", "by wednesday", "by thursday", "by friday", "by saturday", "by sunday",
            "on monday", "on tuesday", "on wednesday", "on thursday", "on friday", "on saturday", "on sunday",
            "next monday", "next tuesday", "next wednesday", "next thursday", "next friday", "next saturday", "next sunday"
        ]
        all_deadlines = strong_deadlines + weak_deadlines

        # 2. Domain Checks
        # School/Education
        school_domains = ["school", "education", "childcare", "little millennium", "times kids"]
        school_keywords = [
            "school", "class", "student", "parent", "teacher", "fee", "homework", 
            "project", "exam", "rehearsal", "competition", "annual day", "sports day", 
            "assignment", "circular", "children", "attendance", "admission"
        ]
        is_school = (
            any(d in msg_lower or d in sender_lower for d in school_domains) or
            any(kw in msg_lower for kw in school_keywords)
        )
        
        # Medical / Insurance
        medical_insurance_keywords = [
            "medical", "hospital", "doctor", "claim", "tpa", "health", "pharmacy", "apollo",
            "insurance", "policy", "premium", "lic", "coverfox", "medi assist", "insurer", "settlement"
        ]
        is_med_ins = any(kw in msg_lower or kw in sender_lower for kw in medical_insurance_keywords)

        # Flat / Society / Rent / Maintenance
        society_keywords = ["flat", "apartment", "society", "association", "maintenance", "rent"]
        is_flat_society = any(kw in msg_lower or kw in sender_lower for kw in society_keywords)

        # 3. Two-Tiered Decision Logic
        should_override = False
        
        # Tier 1: General Domain-Agnostic Action Override
        # Requires a strong action verb AND a strong deadline/time indicator
        has_strong_verb = self._has_word(msg_lower, strong_action_verbs)
        has_strong_deadline = self._has_word(msg_lower, strong_deadlines)
        if has_strong_verb and has_strong_deadline:
            should_override = True
            
        # Tier 2: Domain-Specific Override (School, Medical, Insurance, Society/Flat)
        # In action-sensitive domains, even a single action verb or time indicator is enough
        if not should_override and (is_school or is_med_ins or is_flat_society):
            has_any_verb = self._has_word(msg_lower, all_action_verbs)
            has_any_deadline = self._has_word(msg_lower, all_deadlines)
            if has_any_verb or has_any_deadline:
                should_override = True
                
        # Absolute overrides: anything to do with homework/assignments in school domain is always ACTION
        if not should_override and is_school:
            if self._has_word(msg_lower, ["homework", "assignment"]):
                should_override = True
                
        if should_override:
            # Reclassify to ACTION
            result["signal_type"] = "ACTION"
            result["reason"] = f"SUA Action Override (matched action/deadline conditions)"
            
            # Re-normalize contract format to match ACTION schema requirements
            contract = result.get("contract_json") or {}
            if not isinstance(contract, dict):
                contract = {}
                
            contract["task_name"] = result.get("summary") or "Action Required Alert"
            contract["assignee"] = "parent" if is_school else "user"
            
            # Find a due date indicator if present
            due_date = None
            for d in strong_deadlines + ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
                if d in msg_lower:
                    due_date = d
                    break
            contract["due_date"] = due_date
            result["contract_json"] = contract
            logger.info(f"Overrode signal type to ACTION: {message[:60]}...")
            
        return result

    def _has_word(self, msg: str, words: list) -> bool:
        for w in words:
            pattern = r'\b' + re.escape(w) + r'\b'
            if re.search(pattern, msg):
                return True
        return False

    def _build_prompt(self, message: str, sender: str, source: str, timestamp: str) -> str:
        return f"""Analyze the incoming message and classify it into exactly one of these 4 types:
- FINANCIAL: Active transactions, credit/debit alerts, bank spent/received notifications, payment receipts. (Only if money is actively transferred or spent)
- ACTION: Reminders, todos, tasks, chores, or direct requests to do something (e.g. 'call plumber', 'buy milk').
- FYI: Schedules, bookings, flight/train/movie status, appointments, personal notes, medical info, insurance policies, school updates, or non-actionable info.
- NOISE: Greetings, spam, chit-chat, OTPs, verification codes, promotional codes, marketing, advertisements.

CRITICAL CLASSIFICATION RULES:
1. False Positive (over-classifying as FYI/ACTION/FINANCIAL) is highly preferred over False Negative (classifying as NOISE).
2. Unknown or uncertain messages are NOT Noise. Noise requires positive evidence of being OTP, Spam, Greetings, Promotions, Marketing, or Advertisements.
3. If uncertain between FYI and NOISE, you MUST prefer FYI.
4. The FACT class is retired. Any factual statements, context, or personal info (e.g. medical info, insurance details) must be classified as FYI.

Message details:
Sender: {sender}
Source: {source}
Content: {message}
Timestamp: {timestamp}

Respond ONLY with a single JSON object. Do not wrap in markdown or code blocks.
JSON format keys:
"signal_type" (one of the 4 uppercase types above),
"importance" (float 0.0 to 1.0),
"confidence" (float 0.0 to 1.0),
"summary" (1-sentence description),
"reason" (short classification justification),
"contract" (object of details, e.g. for NOISE it is {{}}).

Contract fields per type:
- FINANCIAL: amount (float), currency (string, e.g. "INR"), transaction_type (DEBIT/CREDIT), payment_channel (UPI/CARD/CASH/UNKNOWN), merchant (string)
- ACTION: task_name (string), assignee (string), due_date (string or null)
- FYI: event_name (string), event_time (string or null), description (string)
- NOISE: {{}}
"""


    def _parse_llm_response(self, text: str) -> dict:
        # Strip markdown code block wrappers if present
        cleaned = text.strip()
        if cleaned.startswith("```"):
            # Remove start block
            cleaned = re.sub(r"^```(?:json)?\n", "", cleaned)
            # Remove end block
            cleaned = re.sub(r"\n```$", "", cleaned)
            cleaned = cleaned.strip()
            
        try:
            data = json.loads(cleaned)
            # Validate basic keys
            required_keys = ["signal_type", "importance", "confidence", "summary", "reason", "contract"]
            if not all(k in data for k in required_keys):
                return None
                
            # Ensure contract is a dict
            if not isinstance(data["contract"], dict):
                return None
                
            # Map LLM contract to contract_json
            return {
                "signal_type": str(data["signal_type"]).upper(),
                "importance": float(data["importance"]),
                "confidence": float(data["confidence"]),
                "summary": str(data["summary"]),
                "reason": str(data["reason"]),
                "contract_json": data["contract"]
            }
        except Exception as e:
            logger.warning(f"Failed to parse JSON from LLM response: {e}. Raw response: {text}")
            return None

    def _fallback_understand(self, signal: dict) -> dict:
        """
        Fallback logic when LLM inference fails or outputs invalid JSON.
        Uses rule-based heuristics to classify common signal formats.
        """
        message = signal.get("message", "")
        msg_lower = message.lower()
        
        signal_type = "FYI"
        importance = 0.3
        confidence = 0.5
        summary = message[:100] + "..." if len(message) > 100 else message
        reason = "Rule-based fallback classification (Default FYI bias)"
        contract = {}
        
        # Simple heuristics for Financial signals
        financial_keywords = ["credited", "debited", "spent", "spent on", "card ending", "upi", "emi", "salary", "payment", "bank", "paid to", "received from", "transferred", "txn", "charges", "due", "pay", "invoice", "bill"]
        if any(kw in msg_lower for kw in financial_keywords):
            signal_type = "FINANCIAL"
            importance = 0.8
            # Try to extract amount
            amount_match = re.search(r"(?:rs\.?|inr)\s*([\d,]+(?:\.\d{2})?)", msg_lower)
            amount = float(amount_match.group(1).replace(",", "")) if amount_match else None
            
            tx_type = "UNKNOWN"
            if "credited" in msg_lower or "received" in msg_lower:
                tx_type = "CREDIT"
            elif "debited" in msg_lower or "spent" in msg_lower or "paid" in msg_lower:
                tx_type = "DEBIT"
                
            contract = {
                "amount": amount,
                "currency": "INR" if amount else None,
                "transaction_type": tx_type,
                "payment_channel": "UPI" if "upi" in msg_lower else "UNKNOWN",
                "merchant": None,
                "transaction_id": None,
                "event_date": signal.get("timestamp")
            }
        # Simple heuristics for Action signals
        elif any(kw in msg_lower for kw in ["remind", "todo", "todo:", "task:", "action:", "buy", "call ", "please", "can you", "could you", "share", "send", "give"]):
            signal_type = "ACTION"
            importance = 0.7
            contract = {
                "task_name": message,
                "assignee": "unknown",
                "due_date": None
            }
            
        return {
            "signal_type": signal_type,
            "importance": importance,
            "confidence": confidence,
            "summary": summary,
            "reason": reason,
            "processing_path": "fallback",
            "llm_model_used": None,
            "contract_json": contract
        }
