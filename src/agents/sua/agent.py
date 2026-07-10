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
                "contract_json": {}
            }
            return self._normalize_contract_fields(result, message)

        # 2. LLM classification path
        prompt = self._build_prompt(message, sender, source, timestamp)
        
        try:
            raw_response = self.llm_client.ask(prompt)
            parsed = self._parse_llm_response(raw_response)
            if parsed:
                parsed["processing_path"] = "llm"
                parsed["llm_model_used"] = self.model
                return self._normalize_contract_fields(parsed, message)
                
        except Exception as e:
            logger.error(f"Error during LLM inference: {e}")
            
        # 3. Fallback heuristics
        fallback_res = self._fallback_understand(signal)
        return self._normalize_contract_fields(fallback_res, message)

    def _normalize_contract_fields(self, result: dict, message: str) -> dict:
        """
        Appends canonical fields to contract_json programmatically.
        """
        contract = result.get("contract_json", {})
        if not isinstance(contract, dict):
            contract = {}
            
        sig_type = result.get("signal_type")
        
        # Inject standard canonical contract fields
        contract["entities"] = extract_entities(message)
        contract["financial_candidate"] = (sig_type == "FINANCIAL")
        contract["fact_candidate"] = (sig_type == "FACT")
        contract["fyi_candidate"] = (sig_type == "FYI")
        contract["noise_candidate"] = (sig_type == "NOISE")
        contract["requires_action"] = (sig_type == "ACTION")
        contract["memory_candidate"] = (sig_type in ["FACT", "ACTION", "FYI"])
        
        result["contract_json"] = contract
        return result

    def _build_prompt(self, message: str, sender: str, source: str, timestamp: str) -> str:
        return f"""Analyze the message and classify it into exactly one of these types:
- FINANCIAL: Active transactions, credit/debit alerts, bank spent/received notifications, payment receipts. (Only if money is actively transferred or spent)
- ACTION: Reminders, todos, tasks, chores, or direct requests to do something (e.g. 'call plumber', 'buy milk').
- FYI: Schedules, bookings, flight/train/movie status, appointments, non-actionable info. (e.g. 'flight AI-101 scheduled')
- FACT: User context, credentials, passport, birthday, height/weight info.
- NOISE: Greetings, spam, chit-chat, OTPs, promotional codes, or generic messages.

Message to analyze:
Sender: {sender}
Source: {source}
Content: {message}
Timestamp: {timestamp}

Respond ONLY with a single JSON object. Do not wrap in markdown or code blocks.
JSON format keys:
"signal_type" (one of the 5 uppercase types above),
"importance" (float 0.0 to 1.0),
"confidence" (float 0.0 to 1.0),
"summary" (1-sentence description),
"reason" (short classification justification),
"contract" (object of details, e.g. for NOISE it is {{}}).

Contract fields per type:
- FINANCIAL: amount, currency, transaction_type (DEBIT/CREDIT), payment_channel (UPI/CARD/CASH/UNKNOWN), merchant
- ACTION: task_name, assignee, due_date
- FYI: event_name, event_time, description
- FACT: entity, attribute, value
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
        
        signal_type = "NOISE"
        importance = 0.1
        confidence = 0.5
        summary = message[:100] + "..." if len(message) > 100 else message
        reason = "Rule-based fallback classification"
        contract = {}
        
        # Simple heuristics for Financial signals
        financial_keywords = ["credited", "debited", "spent", "spent on", "card ending", "upi", "emi", "salary", "payment", "bank", "paid to", "received from", "transferred", "txn"]
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
