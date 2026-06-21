# skills/mobile/mobile_intent_extractor.py

import json
from loguru import logger
from configs.constants import TaskType
from intelligence.routing.router import IntelligenceRouter


class MobileIntentExtractor:

    def __init__(self):
        self.router = IntelligenceRouter()

    def extract_intent(self, signal: dict) -> dict:
        """
        Uses local LLM to classify and structure mobile notifications.
        Returns a dict with intent, category, priority, summary, and details.
        """
        prompt = f"""
You are a mobile notification classifier and information extractor.

Classify the following mobile signal notification.
Return ONLY valid JSON. No explanations, no markdown block wrappers (like ```json), no notes.

Field specifications:
1. "intent": Must be strictly one of these values: "financial_transaction", "otp", "delivery_update", "shopping_order", "school_update", "personal_chat", "work_chat", "important", "ignore".
2. "category": Must be strictly one of these values: "finance", "security", "shopping", "education", "personal", "work", "general".
3. "priority": Must be strictly one of these values: "high", "medium", "low", "ignore".
   - HIGH: For "school_update" or "personal_chat" updates (e.g. spouse, parenting), bank alerts/financial transactions, or urgent action items.
   - MEDIUM: General orders, courier delivery notifications, work updates.
   - LOW: General informational messages, non-urgent receipts.
   - IGNORE: For "otp" (verification codes) or marketing spam.
4. "action_required": Set to true if the notification is a "task" that requires the user to act, false if it is "FYI" (purely informational) or should be ignored.
5. "due_date": YYYY-MM-DD or null if no deadline is specified.
6. "summary": A brief, clear synthesis of the notification message.
7. "details": A JSON object containing key-value pairs depending on the intent:
   
   - If intent is "financial_transaction":
     {{
       "amount": "value (e.g., 1500.00)",
       "currency": "value (e.g., INR)",
       "paid_to": "merchant name or null",
       "paid_from": "source bank name or card suffix or null",
       "receiver_vpa": "VPA handle if present, e.g. target@bank or null",
       "transaction_id": "reference / txn number if present or null",
       "transaction_type": "debit" or "credit",
       "payment_channel": "UPI" or "Credit Card" or "Debit Card" or "Bank Transfer",
       "transaction_status": "successful" or "pending" or "failed"
     }}

   - If intent is "school_update" or "personal_chat":
     {{
       "classification": "FYI" or "task",
       "sender_name": "sender name or null",
       "message_content": "summarized text of the message",
       "action_items": ["list of specific action items if classification is task, otherwise empty list []"]
     }}

   - If intent is "shopping_order" or "delivery_update":
     {{
       "merchant": "merchant or store name or null",
       "product": "product name or null",
       "order_status": "placed/shipped/delivered/out for delivery/etc.",
       "delivery_date": "YYYY-MM-DD or relative time like today or null"
     }}

   - If intent is "otp":
     {{
       "otp_code": "alphanumeric code or null",
       "service": "sender service/bank/app or null"
     }}

   - For other intents, extract any other relevant key-value pairs or leave empty {{}}.

Rules:
- For "school_update" or "personal_chat": Priority must be "high". Classify inside details as "classification": "task" (if action_required is true) or "FYI" (if action_required is false).
- For "otp": Priority must be "ignore". action_required must be false.

Example JSON structure for a WhatsApp school task notification:
{{
  "intent": "school_update",
  "category": "education",
  "priority": "high",
  "summary": "WhatsApp update regarding child science homework due by Wednesday",
  "action_required": true,
  "due_date": "2026-06-25",
  "details": {{
    "classification": "task",
    "sender_name": "Class Group",
    "message_content": "Submit science project model by Wednesday.",
    "action_items": ["Submit science project model"]
  }}
}}

Notification Details:
Source: {signal.get("source")}
Sender: {signal.get("sender")}
Message: {signal.get("message")}

JSON Output:
"""

        try:
            # We classify mobile tasks under TaskType.EMAIL to route locally
            response = self.router.ask(
                prompt=prompt,
                task_type=TaskType.EMAIL,
            )

            logger.info(f"Mobile Signal LLM Raw Response:\n{response}")

            cleaned = (
                response
                .replace("```json", "")
                .replace("```", "")
                .strip()
            )

            # Extract content between first '{' and last '}'
            start_idx = cleaned.find("{")
            end_idx = cleaned.rfind("}")
            if start_idx != -1 and end_idx != -1:
                cleaned = cleaned[start_idx:end_idx + 1]

            result = json.loads(cleaned)

            # Defensive processing for option-list regurgitation
            for field in ["intent", "category", "priority"]:
                if field in result and isinstance(result[field], str) and "|" in result[field]:
                    result[field] = result[field].split("|")[0].strip()

            # Ensure schema validations
            if "intent" not in result:
                result["intent"] = "important"
            if "category" not in result:
                result["category"] = "general"
            if "priority" not in result or str(result["priority"]).lower() not in ("high", "medium", "low", "ignore"):
                result["priority"] = "medium"
            else:
                result["priority"] = str(result["priority"]).lower()
            if "summary" not in result or not result["summary"]:
                result["summary"] = signal.get("message")[:100] if signal.get("message") else "No message text"
            if "action_required" not in result:
                result["action_required"] = False
            if "due_date" not in result:
                result["due_date"] = None
            if "details" not in result or not isinstance(result["details"], dict):
                result["details"] = {}

            # Force specific constraints programmatically as backups
            intent_val = result["intent"]
            if intent_val == "otp":
                result["priority"] = "ignore"
                result["action_required"] = False
            elif intent_val in ("school_update", "personal_chat"):
                result["priority"] = "high"
                details = result["details"]
                if "classification" not in details:
                    details["classification"] = "task" if result["action_required"] else "FYI"
                if details["classification"] == "task":
                    result["action_required"] = True
                else:
                    result["action_required"] = False
                
            return result

        except Exception as e:
            logger.warning(f"Failed to parse mobile intent JSON: {e}. Falling back to default extraction.")
            return self._fallback_extraction(signal)

    def _fallback_extraction(self, signal: dict) -> dict:
        """
        Simple fallback heuristic based on keywords if LLM fails.
        """
        msg_lower = (signal.get("message") or "").lower()
        
        intent = "important"
        category = "general"
        priority = "medium"
        action_required = False
        details = {}
        
        if "school" in msg_lower or "homework" in msg_lower:
            intent = "school_update"
            category = "education"
            priority = "high"
            action_required = "submit" in msg_lower or "homework" in msg_lower
            details = {
                "classification": "task" if action_required else "FYI",
                "sender_name": signal.get("sender"),
                "message_content": signal.get("message"),
                "action_items": [signal.get("message")] if action_required else []
            }
        elif "otp" in msg_lower or "verification code" in msg_lower:
            intent = "otp"
            category = "security"
            priority = "ignore"
            action_required = False
            details = {
                "otp_code": None,
                "service": signal.get("sender")
            }
        elif any(x in msg_lower for x in ["debited", "credited", "spent", "spent on", "card ending", "upi txn"]):
            intent = "financial_transaction"
            category = "finance"
            priority = "high"
            
            import re
            amount_match = re.search(r"(?:rs\.?|inr)\s?([\d,]+(?:\.\d+)?)", msg_lower)
            amount = amount_match.group(1).replace(",", "") if amount_match else None
            details = {
                "amount": amount,
                "currency": "INR",
                "paid_to": None,
                "paid_from": None,
                "receiver_vpa": None,
                "transaction_id": None,
                "transaction_type": "debit" if "debited" in msg_lower or "spent" in msg_lower else "credit",
                "payment_channel": "UPI" if "upi" in msg_lower else None,
                "transaction_status": "successful"
            }
        elif "delivery" in msg_lower or "courier" in msg_lower or "out for delivery" in msg_lower:
            intent = "delivery_update"
            category = "shopping"
            priority = "medium"
            details = {
                "merchant": signal.get("sender"),
                "product": None,
                "order_status": "Out for Delivery" if "out for delivery" in msg_lower else "in transit",
                "delivery_date": "Today" if "today" in msg_lower else None
            }
        
        return {
            "intent": intent,
            "category": category,
            "priority": priority,
            "summary": signal.get("message")[:100] if signal.get("message") else "No message text",
            "action_required": action_required,
            "due_date": None,
            "details": details
        }
