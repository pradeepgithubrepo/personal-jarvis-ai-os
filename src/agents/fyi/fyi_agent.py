"""
src/agents/fyi/fyi_agent.py

Implementation of the FYI Agent V1.
Processes non-actionable signals routed to fyi_agent using a three-lane model:
1. STRUCTURED: Deterministic regex parsing for PNRs, Orders, Claims, and Lockers.
2. RULE_BASED: Keyword matching for promotional, feedback, and routine alerts.
3. LLM: Gemini-first fallback for ambiguous/high-value human-relevant messages.

Owner: FYI Agent
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from loguru import logger

from src.agents.stubs.base_agent_stub import BaseAgentStub, AgentResult
from intelligence.llm_client import LLMClient


class FyiAgent(BaseAgentStub):
    """
    FYI Agent V1 — Context & Information Preservation Agent.
    """

    def __init__(self, provider: str = None, model: str = None):
        self.provider = provider
        self.model = model
        self.llm_client = LLMClient(provider=self.provider, model=self.model)

        # Regex patterns for Lane 1 (Structured Information)
        self.pnr_pattern = re.compile(r"(?i)\bpnr[-:\s]*([a-z0-9]{10,12})\b")
        self.service_pattern = re.compile(r"(?i)\b(JS-[0-9]{10,20})\b")
        self.claim_pattern = re.compile(r"(?i)\bclaim\s*#?\s*([0-9]{8,12})\b")
        self.locker_pattern = re.compile(r"(?i)\blocker\s*(?:no)?\s*#?\s*([a-z0-9\-]+)\b")
        self.order_pattern = re.compile(r"(?i)(?:\border\s*(?:number|no)?\s*#?([0-9\-]{5,20})\b|\b(\d{3}-\d{7}-\d{7})\b)")

        # Keywords for Lane 2 (Known Low-Value/Generic FYI)
        self.promo_keywords = [
            "promotional", "referral", "reward points", "referral link", "referral code",
            "deals are live", "exclusive early", "prime day", "cashback", "cash back",
            "off on your", "early deals", "early access", "reward", "gift is expiring",
            "free hellotune", "hellotune", "roaming pack", "roaming", "subscription",
            "data pack", "data balance", "welcome to the", "track your booking",
            "on-board food", "menu options", "irctc"
        ]
        self.survey_keywords = [
            "feedback", "survey", "thank you for", "thanks for", "choose", "choosing",
            "experience", "happy with", "regrets the temporary", "thank you",
            "folio no", "purchase trxn", "unitholder", "coverfox"
        ]
        self.maint_keywords = [
            "maintenance", "downtime", "unavailable", "consolidation", "upgrade", "upgradation",
            "e-voting", "evoting", "voting begins"
        ]

        # Fix 5a: Lane 2 school informational keywords — deterministic route to FAMILY_SCHOOL
        # Saves LLM calls for routine school circulars that are clearly informational (no action needed)
        self.school_info_keywords = [
            "holiday notice", "term calendar", "school holiday", "no school",
            "parent-teacher", "pta meeting", "sports day notice", "annual day notice",
            "school circular", "school note",
        ]

    @property
    def agent_name(self) -> str:
        return "fyi_agent"

    def process(self, contract: dict) -> AgentResult:
        """
        Synchronous processing stub required by BaseAgentStub interface.
        Pointers are logged, actual processing happens asynchronously via process_pending_routes().
        """
        summary = contract.get("summary", "")
        logger.info(f"fyi_agent: process() called for stub | summary={summary!r}")
        return AgentResult(
            agent_name=self.agent_name,
            status="STUB_ACCEPTED",
            message="FYI Agent registered route decision. Awaiting pull processing.",
            output={"summary": summary},
        )

    def process_pending_routes(self, supabase_client: Any) -> None:
        """
        Queries PENDING routes for fyi_agent in Supabase, classifies them
        using the three-lane architecture, and ingests them into information_items.
        """
        if supabase_client is None:
            logger.error("fyi_agent: Supabase client is uninitialized.")
            return

        logger.info("fyi_agent: Fetching pending signal routes...")
        routes_res = (
            supabase_client.table("signal_routes")
            .select("id, route_status, understood_signal_id")
            .eq("agent_name", self.agent_name)
            .eq("route_status", "PENDING")
            .execute()
        )
        routes = routes_res.data or []
        logger.info(f"fyi_agent: Found {len(routes)} pending route(s).")

        for route in routes:
            route_id = route["id"]
            us_id = route["understood_signal_id"]
            logger.info(f"fyi_agent: Processing route {route_id} (signal {us_id})...")

            try:
                # Fetch Understood Signal detail
                us_res = (
                    supabase_client.table("understood_signals")
                    .select("summary, contract_json, qualified_signals(message, sender, timestamp)")
                    .eq("id", us_id)
                    .single()
                    .execute()
                )
                us_record = us_res.data
                if not us_record:
                    raise ValueError(f"Understood signal {us_id} not found in DB")

                qs = us_record.get("qualified_signals") or {}
                raw_message = qs.get("message") or us_record.get("summary") or ""
                sender = qs.get("sender") or "UNKNOWN"
                orig_timestamp = qs.get("timestamp") or datetime.now(timezone.utc).isoformat()
                contract = us_record.get("contract_json") or {}

                # 1. Classification & Lane Routing
                decision = self._classify_and_route(raw_message, contract)
                
                evt_dt = decision.get("event_datetime")
                if evt_dt and isinstance(evt_dt, str) and evt_dt.strip().lower() in ("null", "none", ""):
                    evt_dt = None

                # 2. Persist to information_items
                info_item = {
                    "route_id": route_id,
                    "processing_path": decision["processing_path"],
                    "category": decision["category"],
                    "title": decision["title"],
                    "summary": decision["summary"],
                    "raw_payload": {
                        "sender": sender,
                        "timestamp": orig_timestamp,
                        "raw_message": raw_message,
                        "contract": contract
                    },
                    "event_datetime": evt_dt,
                    "timeline_group_id": decision["timeline_group_id"],
                    "importance_level": decision["importance_level"]
                }
                
                supabase_client.table("information_items").insert(info_item).execute()
                logger.info(f"fyi_agent: Created info item via {decision['processing_path']}: {decision['title']!r}")

                # 3. Mark route as COMPLETED
                self._update_route_status(supabase_client, route_id, "COMPLETED")

            except Exception as e:
                logger.error(f"fyi_agent: Failed to process route {route_id}: {e}")
                self._update_route_status(supabase_client, route_id, "FAILED", error_message=str(e))

    def _classify_and_route(self, raw_message: str, contract: dict) -> dict:
        """
        Classifies incoming signal text using the three-lane model:
        STRUCTURED -> RULE_BASED -> LLM.
        """
        msg_clean = raw_message.strip()
        msg_lower = msg_clean.lower()

        # ========================================================
        # LANE 1: STRUCTURED (No LLM, Regex Pattern Matching)
        # ========================================================
        pnr_match = self.pnr_pattern.search(msg_clean)
        if pnr_match:
            pnr = pnr_match.group(1)
            return {
                "processing_path": "STRUCTURED",
                "category": "TRAVEL",
                "title": f"Train Ticket Info (PNR: {pnr})",
                "summary": f"Booking details for Train ticket under PNR {pnr}.",
                "event_datetime": contract.get("type_specific", {}).get("departure_time") or contract.get("due_date"),
                "timeline_group_id": f"train-{pnr}",
                "importance_level": "MEDIUM"
            }

        service_match = self.service_pattern.search(msg_clean)
        if service_match:
            ticket = service_match.group(1)
            return {
                "processing_path": "STRUCTURED",
                "category": "TRAVEL",
                "title": f"Service Request Status ({ticket})",
                "summary": f"Service request updates and door-step details for request {ticket}.",
                "event_datetime": None,
                "timeline_group_id": f"service-{ticket.lower()}",
                "importance_level": "MEDIUM"
            }

        claim_match = self.claim_pattern.search(msg_clean)
        if claim_match:
            claim = claim_match.group(1)
            return {
                "processing_path": "STRUCTURED",
                "category": "FINANCE_INSURANCE",
                "title": f"Medi Assist Claim processed (Claim: {claim})",
                "summary": f"Reimbursement claim details for Medi Assist Claim {claim}.",
                "event_datetime": None,
                "timeline_group_id": f"claim-{claim}",
                "importance_level": "HIGH"
            }

        locker_match = self.locker_pattern.search(msg_clean)
        if locker_match:
            locker = locker_match.group(1)
            return {
                "processing_path": "STRUCTURED",
                "category": "SECURITY_ALERT",
                "title": f"Locker Operated (Locker: {locker})",
                "summary": f"Notification regarding locker operations for Locker No {locker}.",
                "event_datetime": None,
                "timeline_group_id": f"locker-{locker.lower()}",
                "importance_level": "CRITICAL"
            }

        order_match = self.order_pattern.search(msg_clean)
        if order_match:
            order_id = order_match.group(1) or order_match.group(2)
            # Find status (shipped, delivered, dispatch)
            status = "Update"
            if "shipped" in msg_lower:
                status = "Shipped"
            elif "delivered" in msg_lower:
                status = "Delivered"
            elif "confirm" in msg_lower:
                status = "Confirmed"
            elif "dispatch" in msg_lower:
                status = "Dispatched"
                
            return {
                "processing_path": "STRUCTURED",
                "category": "ORDER_TRACKING",
                "title": f"Order #{order_id} {status}",
                "summary": f"Delivery and status update for order #{order_id}.",
                "event_datetime": None,
                "timeline_group_id": f"order-{order_id}",
                "importance_level": "MEDIUM"
            }

        # ========================================================
        # LANE 2: RULE_BASED (No LLM, Low-Value / Generic Keywords)
        # ========================================================
        if any(kw in msg_lower for kw in self.promo_keywords):
            return {
                "processing_path": "RULE_BASED",
                "category": "GENERAL",
                "title": "Reward / Promotional Offer",
                "summary": msg_clean[:100] + ("..." if len(msg_clean) > 100 else ""),
                "event_datetime": None,
                "timeline_group_id": None,
                "importance_level": "LOW"
            }

        if any(kw in msg_lower for kw in self.survey_keywords):
            return {
                "processing_path": "RULE_BASED",
                "category": "GENERAL",
                "title": "Customer Feedback Request",
                "summary": msg_clean[:100] + ("..." if len(msg_clean) > 100 else ""),
                "event_datetime": None,
                "timeline_group_id": None,
                "importance_level": "LOW"
            }

        if any(kw in msg_lower for kw in self.maint_keywords):
            return {
                "processing_path": "RULE_BASED",
                "category": "UTILITY_INFO",
                "title": "Service Maintenance / Consolidation Alert",
                "summary": msg_clean[:100] + ("..." if len(msg_clean) > 100 else ""),
                "event_datetime": None,
                "timeline_group_id": None,
                "importance_level": "MEDIUM"
            }

        # Fix 5a: Lane 2 — school informational (holiday notices, PTA, annual day — no obligation)
        if any(kw in msg_lower for kw in self.school_info_keywords):
            return {
                "processing_path": "RULE_BASED",
                "category": "FAMILY_SCHOOL",
                "title": "School Notice / Parent Circular",
                "summary": msg_clean[:150] + ("..." if len(msg_clean) > 150 else ""),
                "event_datetime": None,
                "timeline_group_id": None,
                "importance_level": "HIGH"
            }

        # ========================================================
        # LANE 2.5: RULE_BASED (Conversational & Short Chat / Status Updates)
        # ========================================================
        # Any message under 80 characters that does not contain high-value
        # domain keywords is processed deterministically to bypass the LLM.
        llm_domain_keywords = [
            "homework", "parent", "orientation", "pop", "school",
            "doctor", "colonoscopy", "endoscopy", "enema", "prep", "medical",
            "tenant", "lease", "rent", "agreement", "cyber", "fraud", "police"
        ]
        
        has_llm_keyword = any(kw in msg_lower for kw in llm_domain_keywords)
        starts_with_media = msg_clean.startswith("📷") or msg_clean.startswith("📄")
        
        if (len(msg_clean) < 80 and not has_llm_keyword) or (starts_with_media and not has_llm_keyword):
            # Categorize as TRAVEL if transit terms are found
            transit_keywords = ["train", "boarded", "started", "reached", "home", "office", "arrived", "departs", "gate", "parking"]
            is_transit = any(kw in msg_lower for kw in transit_keywords)
            category = "TRAVEL" if is_transit else "GENERAL"
            
            # Simple title heuristics
            if msg_clean.startswith("📷"):
                title = "Media Receipt (Photo)"
            elif msg_clean.startswith("📄"):
                title = "Document Receipt"
            elif is_transit:
                title = "Transit / Location Status"
            else:
                title = "Short Message / Chat Alert"
                
            return {
                "processing_path": "RULE_BASED",
                "category": category,
                "title": title,
                "summary": msg_clean,
                "event_datetime": None,
                "timeline_group_id": None,
                "importance_level": "EPHEMERAL"
            }

        # ========================================================
        # LANE 3: AMBIGUOUS (LLM reasoning required)
        # ========================================================
        return self._reason_over_fyi(msg_clean, contract)

    def _reason_over_fyi(self, raw_message: str, contract: dict) -> dict:
        """
        Invokes LLM fallback hierarchy to synthesize and categorize ambiguous FYI messages.
        """
        prompt = f"""
Analyze the incoming FYI signal, classify its category, and determine its importance_level.

Categories allowed:
- TRAVEL: flight, train, hotel, or travel schedule context.
- ORDER_TRACKING: order details, package shipping, courier.
- SECURITY_ALERT: operations on lockers, security warnings, verification notices.
- FAMILY_SCHOOL: school homework, children orientation programs, school updates.
- HEALTH: prescriptions, doctor consulting, hospital visits, medical test prep.
- FINANCE_INSURANCE: insurance renewals, policy summaries, bank transactions, evoting.
- UTILITY_INFO: service maintenance, consolidation updates.
- GENERAL: general details, status alerts, generic context.

Importance Levels:
- CRITICAL: Hospitalization alerts, school emergencies, security/locker alarms, policy expiry warnings, major financial transactions.
- HIGH: Routine school homework, doctor prescriptions, medical test appointments, tenant name/lease details, active insurance summaries.
- MEDIUM: Order status/shipping updates, train/flight status, location check-ins.
- LOW: Telecom offers, Prime Day sales, feedback survey requests, marketing/promo flyers.
- EPHEMERAL: Short conversational updates (greetings, 'Okay', 'Reach home'), reaction updates, raw media attachments.

Incoming Signal Text:
"{raw_message}"

Signal Context Contract:
{json.dumps(contract, indent=2)}

Instructions:
1. Provide a title-cased clean title summarizing the event.
2. Provide a concise, one-sentence summary description of the information.
3. Determine category (MUST be exactly one of the allowed categories list, do not use combinations or delimiters).
4. Determine importance_level (MUST be exactly one of the allowed importance levels list).
5. Extract event_datetime if an explicit occurrence date/time is mentioned.

You MUST return a raw JSON object ONLY, conforming EXACTLY to this schema (no surrounding markdown code blocks, no backticks, just raw JSON):
{{
  "category": "TRAVEL | ORDER_TRACKING | SECURITY_ALERT | FAMILY_SCHOOL | HEALTH | FINANCE_INSURANCE | UTILITY_INFO | GENERAL",
  "importance_level": "CRITICAL | HIGH | MEDIUM | LOW | EPHEMERAL",
  "title": "Clean Title",
  "summary": "One-sentence summary description",
  "event_datetime": "ISO_TIMESTAMP or null",
  "rationale": "Short explanation of your reasoning"
}}
"""
        # Execute ask with fallback
        try:
            raw_response = self.llm_client.ask(prompt)
            clean_res = raw_response.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(clean_res)
            
            # Fix 5b: Post-process category — broader match to ensure FAMILY_SCHOOL is actually applied
            cat = parsed.get("category") or "GENERAL"
            cat = cat.strip().upper()
            if "TRAVEL" in cat:
                category = "TRAVEL"
            elif "ORDER_TRACKING" in cat or "ORDER" in cat:
                category = "ORDER_TRACKING"
            elif "SECURITY_ALERT" in cat or "SECURITY" in cat:
                category = "SECURITY_ALERT"
            elif ("FAMILY_SCHOOL" in cat or "FAMILY" in cat or "SCHOOL" in cat
                  or "PARENT" in cat or "EDUCATION" in cat or "CHILD" in cat):
                category = "FAMILY_SCHOOL"
            elif "HEALTH" in cat or "MEDICAL" in cat:
                category = "HEALTH"
            elif "FINANCE_INSURANCE" in cat or "INSURANCE" in cat or "FINANCE" in cat:
                category = "FINANCE_INSURANCE"
            elif "UTILITY_INFO" in cat or "UTILITY" in cat:
                category = "UTILITY_INFO"
            else:
                category = "GENERAL"

            # Post-process importance level
            imp = parsed.get("importance_level") or "MEDIUM"
            imp = imp.strip().upper()
            if imp not in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "EPHEMERAL"]:
                imp = "MEDIUM"
            
            path = "LLM_GEMINI"
            if not self.llm_client.gemini_api_key:
                path = "LLM_CEREBRAS" if self.llm_client.cerebras_api_key else "LLM_LOCAL"
                
            return {
                "processing_path": path,
                "category": category,
                "importance_level": imp,
                "title": parsed.get("title") or "General Informational Alert",
                "summary": parsed.get("summary") or raw_message,
                "event_datetime": parsed.get("event_datetime") or contract.get("due_date"),
                "timeline_group_id": self._generate_deterministic_timeline_id(parsed.get("title", ""), raw_message)
            }
        except Exception as e:
            logger.warning(f"fyi_agent: LLM reasoning failed: {e}. Falling back to rule-based parser.")
            return {
                "processing_path": "LLM_LOCAL",
                "category": "GENERAL",
                "importance_level": "MEDIUM",
                "title": contract.get("task_name") or "General Informational Notice",
                "summary": raw_message[:150] + ("..." if len(raw_message) > 150 else ""),
                "event_datetime": contract.get("due_date"),
                "timeline_group_id": self._generate_deterministic_timeline_id("", raw_message)
            }

    def _generate_deterministic_timeline_id(self, title: str, message: str) -> str | None:
        """
        Attempts to compute a deterministic timeline_group_id from message text in Lane 3
        if any secondary structured terms appear (e.g. order numbers or PNRs).
        """
        msg_lower = message.lower()
        
        # Check order numbers
        order_match = self.order_pattern.search(message)
        if order_match:
            return f"order-{order_match.group(1)}"
            
        # Check PNRs
        pnr_match = self.pnr_pattern.search(message)
        if pnr_match:
            return f"train-{pnr_match.group(1)}"
            
        # Check claim IDs
        claim_match = self.claim_pattern.search(message)
        if claim_match:
            return f"claim-{claim_match.group(1)}"
            
        return None

    def _update_route_status(self, supabase_client: Any, route_id: str, status: str, error_message: str = None) -> None:
        """
        Updates the routing record status in Supabase.
        """
        update_data = {
            "route_status": status,
            "completed_at": datetime.now(timezone.utc).isoformat() if status == "COMPLETED" else None,
            "error_message": error_message
        }
        supabase_client.table("signal_routes").update(update_data).eq("id", route_id).execute()
        logger.info(f"fyi_agent: Updated route {route_id} status to {status}")
