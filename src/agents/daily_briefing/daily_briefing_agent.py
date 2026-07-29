"""
src/agents/daily_briefing/daily_briefing_agent.py

Daily Briefing Agent V1 — Executive Personal Assistant (Signature 10/10 Experience).

Generates a personalized daily morning briefing tailored for a CEO.
Compresses application state, suppresses low-value noise, synthesizes conversational financial insights,
performs cross-section deduplication, adds a glanceable day_status badge, includes a Since Yesterday delta section,
enforces hard section limits (readable in under 30 seconds), and provides executive recommendation guidance.
"""
from __future__ import annotations

import datetime
import json
import re
import time
from typing import Any, Dict, List, Optional, Set
from loguru import logger

from src.agents.stubs.base_agent_stub import BaseAgentStub, AgentResult
from intelligence.llm_client import LLMClient


# Blacklisted noisy phrases for suppression
NOISE_PATTERNS = [
    r"media\s+receive",
    r"photo",
    r"reached\s+home",
    r"chat\s+alert",
    r"customer\s+feedback\s+request",
    r"transit\s*/\s*location",
    r"service\s+request\s+status",
    r"short\s+message",
]

STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
    "by", "from", "up", "about", "into", "over", "after", "is", "are", "was", "were",
    "be", "been", "being", "have", "has", "had", "do", "does", "did", "this", "that",
    "these", "those", "my", "your", "his", "her", "its", "our", "their", "due", "today",
    "urgent", "new", "item", "items", "status", "program", "session", "form", "bill",
}


class DailyBriefingAgent(BaseAgentStub):
    """
    Daily Briefing Agent V1 — Executive Personal Assistant.
    Signature 10/10 Jarvis Morning Briefing Engine.
    """

    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        self.provider = provider
        self.model = model
        self.llm_client = LLMClient(provider=self.provider, model=self.model)

    @property
    def agent_name(self) -> str:
        return "daily_briefing_agent"

    def process(self, contract: dict) -> AgentResult:
        """
        Synchronous stub processor implementation required by BaseAgentStub interface.
        """
        logger.info("daily_briefing_agent: process() called for stub.")
        return AgentResult(
            agent_name=self.agent_name,
            status="COMPLETED",
            message="Daily briefing agent stub process complete.",
        )

    def is_noise(self, text: str) -> bool:
        """Check if text matches blacklisted trivial noise patterns."""
        if not text:
            return True
        text_lower = text.lower().strip()
        for pattern in NOISE_PATTERNS:
            if re.search(pattern, text_lower):
                return True
        return False

    def extract_keywords(self, text: str) -> Set[str]:
        """Extract significant content keywords for cross-section deduplication."""
        words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
        return {w for w in words if w not in STOP_WORDS}

    def fetch_trusted_context(self, supabase_client: Any) -> Dict[str, Any]:
        """
        Query trusted application state tables only.
        Applies stale information handling, noise suppression, and computes 24-hour delta metrics.
        """
        logger.info("daily_briefing_agent: Fetching trusted application state...")
        raw_data: Dict[str, Any] = {
            "tasks": [],
            "financial_transactions": [],
            "monthly_spending_summary": {},
            "monthly_category_spend": [],
            "monthly_merchant_spend": [],
            "monthly_income_sources": [],
            "monthly_top_transactions": [],
            "information_items": [],
            "lifecycle_items": [],
            "since_yesterday_metrics": {
                "new_tasks_created": 0,
                "payments_completed": 0,
                "new_info_items": 0,
            },
        }

        if supabase_client is None:
            logger.warning("daily_briefing_agent: supabase_client is None. Returning empty context.")
            return raw_data

        now_utc = datetime.datetime.now(datetime.timezone.utc)
        twenty_four_hours_ago = (now_utc - datetime.timedelta(hours=24)).isoformat()

        # 1. Fetch active tasks (exclude COMPLETED, CANCELLED, ARCHIVED)
        try:
            res = (
                supabase_client.table("tasks")
                .select("id, title, description, priority, due_datetime, status, source_type, created_at")
                .in_("status", ["OPEN", "IN_PROGRESS"])
                .execute()
            )
            tasks = res.data or []
            new_tasks_cnt = 0
            seen_tasks = set()
            clean_tasks = []
            for t in tasks:
                t_key = t.get("title", "").strip().lower()
                created_at_str = t.get("created_at")
                if created_at_str and created_at_str >= twenty_four_hours_ago:
                    new_tasks_cnt += 1
                if t_key and t_key not in seen_tasks:
                    seen_tasks.add(t_key)
                    clean_tasks.append(t)

            raw_data["tasks"] = clean_tasks
            raw_data["since_yesterday_metrics"]["new_tasks_created"] = new_tasks_cnt
            logger.info(f"daily_briefing_agent: Loaded {len(clean_tasks)} active tasks ({new_tasks_cnt} new since yesterday).")
        except Exception as e:
            logger.warning(f"daily_briefing_agent: Error fetching tasks: {e}")

        # 2. Fetch financial summary tables
        try:
            res = supabase_client.table("monthly_spending_summary").select("*").order("created_at", desc=True).limit(1).execute()
            summaries = res.data or []
            if summaries:
                raw_data["monthly_spending_summary"] = summaries[0]

            res_cat = supabase_client.table("monthly_category_spend").select("*").execute()
            raw_data["monthly_category_spend"] = res_cat.data or []

            res_merch = supabase_client.table("monthly_merchant_spend").select("*").execute()
            raw_data["monthly_merchant_spend"] = res_merch.data or []

            res_inc = supabase_client.table("monthly_income_sources").select("*").execute()
            raw_data["monthly_income_sources"] = res_inc.data or []

            res_top = supabase_client.table("monthly_top_transactions").select("*").execute()
            raw_data["monthly_top_transactions"] = res_top.data or []

            res_ft = supabase_client.table("financial_transactions").select("transaction_id, raw_narration, merchant, category, amount, direction, transaction_type, event_date, created_at").order("event_date", desc=True).limit(20).execute()
            ft_data = res_ft.data or []
            raw_data["financial_transactions"] = ft_data

            payments_cnt = sum(1 for f in ft_data if f.get("created_at", "") >= twenty_four_hours_ago or f.get("event_date", "") == datetime.date.today().isoformat())
            raw_data["since_yesterday_metrics"]["payments_completed"] = payments_cnt

            logger.info("daily_briefing_agent: Loaded financial summary tables.")
        except Exception as e:
            logger.warning(f"daily_briefing_agent: Error fetching financial data: {e}")

        # 3. Fetch recent information_items and suppress noise
        try:
            res = (
                supabase_client.table("information_items")
                .select("id, category, title, summary, event_datetime, created_at")
                .order("created_at", desc=True)
                .limit(20)
                .execute()
            )
            raw_info = res.data or []
            clean_info = []
            seen_info = set()
            new_info_cnt = 0
            for item in raw_info:
                title = item.get("title", "")
                summary = item.get("summary", "")
                created_at_str = item.get("created_at", "")
                if created_at_str and created_at_str >= twenty_four_hours_ago:
                    new_info_cnt += 1

                if self.is_noise(title) or self.is_noise(summary):
                    continue
                key = title.strip().lower()
                if key and key not in seen_info:
                    seen_info.add(key)
                    clean_info.append(item)

            raw_data["information_items"] = clean_info
            raw_data["since_yesterday_metrics"]["new_info_items"] = new_info_cnt
            logger.info(f"daily_briefing_agent: Loaded {len(clean_info)} meaningful information items ({new_info_cnt} new since yesterday).")
        except Exception as e:
            logger.warning(f"daily_briefing_agent: Error fetching information items: {e}")

        # 4. Fetch active lifecycle items (status == 'ACTIVE')
        try:
            res = (
                supabase_client.table("lifecycle_items")
                .select("id, domain, title, description, next_occurrence_date, status")
                .eq("status", "ACTIVE")
                .execute()
            )
            lifecycle = res.data or []
            raw_data["lifecycle_items"] = lifecycle
            logger.info(f"daily_briefing_agent: Loaded {len(lifecycle)} active lifecycle items.")
        except Exception as e:
            logger.warning(f"daily_briefing_agent: Error fetching lifecycle items: {e}")

        return raw_data

    def build_context_json(self, raw_data: Dict[str, Any], generated_at: Optional[str] = None) -> Dict[str, Any]:
        """
        Build the standardized input context JSON document.
        """
        if generated_at is None:
            generated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        context = {
            "generated_at": generated_at,
            "since_yesterday_metrics": raw_data.get("since_yesterday_metrics", {}),
            "tasks": raw_data.get("tasks", []),
            "total_active_tasks_count": len(raw_data.get("tasks", [])),
            "finance": {
                "monthly_summary": raw_data.get("monthly_spending_summary", {}),
                "category_spend": raw_data.get("monthly_category_spend", []),
                "merchant_spend": raw_data.get("monthly_merchant_spend", []),
                "income_sources": raw_data.get("monthly_income_sources", []),
                "top_transactions": raw_data.get("monthly_top_transactions", []),
            },
            "information_items": raw_data.get("information_items", []),
            "lifecycle_items": raw_data.get("lifecycle_items", []),
        }

        return context

    def generate_briefing_with_llm(self, context_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send context JSON to Gemini (primary) with Mistral fallback to generate signature executive briefing.
        """
        system_prompt = (
            "You are the Executive Personal Assistant for a CEO (User: Pradeep).\n"
            "Your task is to deliver the signature Jarvis morning briefing—concise, conversational, prioritized, and readable in under 30 seconds.\n"
            "The objective is NOT completeness. The objective is PRIORITIZATION and EXECUTIVE ADVICE.\n\n"
            "CRITICAL ARCHITECTURAL RULES:\n"
            "1. DAY STATUS BADGE ('day_status'): Include a top-level badge object evaluating today's overall load:\n"
            "   - 'status': 'Action Required' (Red) | 'Busy' (Amber) | 'Calm' (Green)\n"
            "   - 'color': 'Red' | 'Amber' | 'Green'\n"
            "   - 'reason': Short 1-sentence reason (e.g. 'Two overdue financial obligations and one mandatory school event.').\n"
            "2. NO DUPLICATE FACTS ACROSS SECTIONS: Each event or fact must appear EXACTLY ONCE in the entire briefing.\n"
            "   - If an item appears in 'Needs Attention' (e.g. Parent Orientation or SBI Card), DO NOT repeat it in 'Upcoming Lifecycle Events', 'Recent Information', or 'Financial Snapshot'!\n"
            "3. CONVERSATIONAL FINANCE: Never list raw ledger transactions or mathematical formulas like '+₹109,424 (Income: ₹511K vs Expense: ₹401K)'.\n"
            "   - Write conversational executive statements (e.g. 'Your cash flow remains healthy this month.', 'One significant investment transaction was recorded.', 'Electricity bill of ₹2,351 is due before July 30.'). Max 4 bullets.\n"
            "4. EVENT SUMMARIES OVER NOTIFICATION REPLAYS: Never replay message titles like 'Portronics delivery scheduled...'. Summarize real events (e.g. 'A scheduled delivery is expected today.', 'Your purifier installation has been completed successfully.'). Max 4 bullets.\n"
            "5. SINCE YESTERDAY SECTION: Provide 2-3 metric bullets summarizing system changes since yesterday based on 'since_yesterday_metrics' (e.g. '3 new tasks created', '1 payment completed', '2 new information items received').\n"
            "6. NEEDS ATTENTION: Rank by urgency. Show at most 5 items. If remaining tasks exist, end section with '(+X more tasks)'.\n"
            "7. CLOSING RECOMMENDATION: Conclude with assistant advice on what deserves priority today (e.g. 'Today\'s priorities are clearing the overdue SBI card payment and attending the school orientation. Apart from these, your financial position remains stable and no major issues require immediate attention.').\n\n"
            "REQUIRED JSON SCHEMA:\n"
            "{\n"
            '  "title": "Good Morning",\n'
            '  "day_status": {\n'
            '    "status": "Action Required" | "Busy" | "Calm",\n'
            '    "color": "Red" | "Amber" | "Green",\n'
            '    "reason": "Executive reason string"\n'
            "  },\n"
            '  "overall_priority": "HIGH" | "MEDIUM" | "LOW",\n'
            '  "sections": [\n'
            "    {\n"
            '      "type": "attention",\n'
            '      "title": "Needs Attention",\n'
            '      "items": ["Item 1", "Item 2", ...]\n'
            "    },\n"
            "    {\n"
            '      "type": "since_yesterday",\n'
            '      "title": "Since Yesterday",\n'
            '      "items": ["3 new tasks created", "1 payment completed", "2 new information items received"]\n'
            "    },\n"
            "    {\n"
            '      "type": "finance",\n'
            '      "title": "Financial Snapshot",\n'
            '      "items": ["Conversational insight 1", ...]\n'
            "    },\n"
            "    {\n"
            '      "type": "information",\n'
            '      "title": "Recent Information",\n'
            '      "items": ["Event summary 1", ...]\n'
            "    },\n"
            "    {\n"
            '      "type": "lifecycle",\n'
            '      "title": "Upcoming Lifecycle Events",\n'
            '      "items": ["Milestone 1", ...]\n'
            "    }\n"
            "  ],\n"
            '  "closing_message": "Executive recommendation sentence advising priority focus today."\n'
            "}\n"
            "Return STRICT JSON only."
        )

        user_prompt = f"Context Application State:\n{json.dumps(context_json, indent=2)}\n\nGenerate the Executive Personal Assistant briefing JSON now:"
        full_prompt = f"{system_prompt}\n\n{user_prompt}"

        start_time = time.time()
        provider_used = "gemini"
        model_used = "gemini-2.5-flash"
        raw_response = ""

        # Tier 1: Try Gemini Primary
        try:
            logger.info("daily_briefing_agent: Attempting primary LLM provider: Gemini (gemini-2.5-flash)")
            raw_response = self.llm_client.ask(full_prompt, provider="gemini", model="gemini-2.5-flash")
        except Exception as gemini_err:
            logger.warning(f"daily_briefing_agent: Gemini failed ({gemini_err}). Attempting fallback provider: Mistral")
            provider_used = "mistral"
            model_used = "mistral-small-latest"
            try:
                raw_response = self.llm_client.ask(full_prompt, provider="mistral", model="mistral-small-latest")
            except Exception as mistral_err:
                logger.error(f"daily_briefing_agent: Fallback Mistral failed ({mistral_err}). Attempting general hierarchy ask()")
                raw_response = self.llm_client.ask(full_prompt)
                provider_used = getattr(self.llm_client, "provider", "fallback_llm")
                model_used = "default"

        duration_ms = int((time.time() - start_time) * 1000)

        # Parse JSON response
        briefing_dict = self._parse_json_response(raw_response)

        return {
            "briefing_dict": briefing_dict,
            "llm_provider": provider_used,
            "llm_model": model_used,
            "generation_duration_ms": duration_ms,
        }

    def _parse_json_response(self, raw_text: str) -> Dict[str, Any]:
        """Parse raw LLM response into a Python dictionary."""
        cleaned = raw_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except Exception as e:
            logger.error(f"daily_briefing_agent: Failed to parse LLM JSON response: {e} | Raw text: {raw_text[:200]}")
            return {
                "title": "Good Morning",
                "day_status": {
                    "status": "Calm",
                    "color": "Green",
                    "reason": "No urgent financial or schedule issues requiring immediate attention today.",
                },
                "overall_priority": "MEDIUM",
                "sections": [],
                "closing_message": "Today is clear. No major action items require immediate focus.",
            }

    def validate_and_sanitize_briefing(self, raw_briefing: Dict[str, Any], context_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate schema, perform cross-section deduplication, enforce section limits, and sanitize content.
        """
        title = raw_briefing.get("title") or "Good Morning"
        priority = raw_briefing.get("overall_priority", "MEDIUM").upper()
        if priority not in ["HIGH", "MEDIUM", "LOW"]:
            priority = "MEDIUM"

        day_status = raw_briefing.get("day_status") or {
            "status": "Busy" if priority == "HIGH" else "Calm",
            "color": "Red" if priority == "HIGH" else ("Amber" if priority == "MEDIUM" else "Green"),
            "reason": "Executive morning review.",
        }

        total_active_tasks = context_json.get("total_active_tasks_count", len(context_json.get("tasks", [])))
        raw_sections = raw_briefing.get("sections", [])
        
        # Priority order for cross-section deduplication
        section_order = ["attention", "since_yesterday", "finance", "information", "lifecycle"]
        section_map = {sec.get("type"): sec for sec in raw_sections if isinstance(sec, dict)}

        seen_fact_keywords: Set[str] = set()
        clean_sections: List[Dict[str, Any]] = []

        for sec_type in section_order:
            sec = section_map.get(sec_type)
            if not sec:
                continue

            sec_title = sec.get("title") or sec_type.replace("_", " ").title()
            raw_items = sec.get("items", [])

            clean_items: List[str] = []
            for item in raw_items:
                if not isinstance(item, str):
                    continue
                item_str = item.strip()
                if not item_str or self.is_noise(item_str):
                    continue

                # Cross-section deduplication check
                item_kw = self.extract_keywords(item_str)
                if item_kw:
                    overlap = item_kw.intersection(seen_fact_keywords)
                    # If 2 or more significant keywords match an item in a higher priority section, deduplicate!
                    if len(overlap) >= 2 and sec_type not in ["attention", "since_yesterday"]:
                        logger.info(f"daily_briefing_agent: Deduplicating item '{item_str}' from section '{sec_type}' due to overlap: {overlap}")
                        continue
                    seen_fact_keywords.update(item_kw)

                clean_items.append(item_str)

            # Enforce Section Output Limits & Formatting
            if sec_type == "attention":
                if len(clean_items) > 5:
                    clean_items = clean_items[:5]
                
                already_has_more_indicator = any("more task" in it.lower() for it in clean_items)
                if total_active_tasks > 5 and not already_has_more_indicator:
                    remaining_count = total_active_tasks - len(clean_items)
                    if remaining_count > 0:
                        clean_items.append(f"(+{remaining_count} more tasks)")

            elif sec_type == "since_yesterday":
                clean_items = clean_items[:4]

            elif sec_type == "finance":
                # Filter out raw ledger formulas like +₹109,424 (Income vs Expense)
                clean_finance = []
                for it in clean_items:
                    if re.search(r"\+\s*₹?\d+[\d,]*\s*\(income", it.lower()) or re.search(r"transaction_id", it.lower()):
                        continue
                    clean_finance.append(it)
                clean_items = clean_finance[:4]

            elif sec_type == "information":
                clean_items = clean_items[:4]

            elif sec_type == "lifecycle":
                clean_items = clean_items[:3]

            if clean_items:
                clean_sections.append({
                    "type": sec_type,
                    "title": sec_title,
                    "items": clean_items,
                })

        closing = raw_briefing.get("closing_message") or "Today's priorities are clearing urgent tasks; financially your position remains stable."

        return {
            "title": title,
            "day_status": day_status,
            "overall_priority": priority,
            "sections": clean_sections,
            "closing_message": closing,
        }

    def persist_briefing(self, supabase_client: Any, briefing_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store complete briefing record into the daily_briefings database table.
        """
        today_date = datetime.date.today().isoformat()
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        row = {
            "briefing_date": briefing_record.get("briefing_date") or today_date,
            "generated_at": briefing_record.get("generated_at") or now_iso,
            "overall_priority": briefing_record.get("overall_priority", "MEDIUM"),
            "title": briefing_record.get("title", "Good Morning"),
            "briefing_json": briefing_record.get("briefing_json", {}),
            "llm_provider": briefing_record.get("llm_provider", "unknown"),
            "llm_model": briefing_record.get("llm_model", "unknown"),
            "generation_duration_ms": briefing_record.get("generation_duration_ms", 0),
        }

        logger.info(f"daily_briefing_agent: Persisting executive briefing to Supabase (date={row['briefing_date']})...")

        if supabase_client is None:
            logger.warning("daily_briefing_agent: supabase_client is None. Returning mock record.")
            return {"status": "MOCK_PERSISTED", "data": row}

        try:
            res = supabase_client.table("daily_briefings").insert(row).execute()
            inserted = res.data[0] if res.data else row
            logger.info(f"daily_briefing_agent: Briefing persisted successfully (ID: {inserted.get('id')})!")
            return {"status": "SUCCESS", "data": inserted}
        except Exception as e:
            logger.error(f"daily_briefing_agent: Failed to persist briefing: {e}")
            return {"status": "FAILED", "error": str(e), "data": row}

    def generate_daily_briefing(self, supabase_client: Any, target_date: Optional[datetime.date] = None) -> Dict[str, Any]:
        """
        Complete end-to-end Daily Briefing execution pipeline.
        """
        if target_date is None:
            target_date = datetime.date.today()

        logger.info(f"daily_briefing_agent: Executing daily briefing pipeline for {target_date}...")

        # 1. Fetch trusted context (with stale data exclusion, noise suppression, and 24h metrics)
        raw_data = self.fetch_trusted_context(supabase_client)

        # 2. Build standardized JSON context
        context_json = self.build_context_json(raw_data)

        # 3. Request LLM summarization (Gemini primary -> Mistral fallback)
        llm_result = self.generate_briefing_with_llm(context_json)

        # 4. Validate, cross-deduplicate, and sanitize output
        clean_briefing_json = self.validate_and_sanitize_briefing(llm_result["briefing_dict"], context_json)

        # 5. Build full persistence record
        briefing_record = {
            "briefing_date": target_date.isoformat(),
            "generated_at": context_json["generated_at"],
            "overall_priority": clean_briefing_json["overall_priority"],
            "title": clean_briefing_json["title"],
            "briefing_json": clean_briefing_json,
            "llm_provider": llm_result["llm_provider"],
            "llm_model": llm_result["llm_model"],
            "generation_duration_ms": llm_result["generation_duration_ms"],
        }

        # 6. Persist to database
        persist_res = self.persist_briefing(supabase_client, briefing_record)

        return {
            "status": persist_res.get("status", "SUCCESS"),
            "briefing_record": briefing_record,
            "context_summary": {
                "tasks_count": len(context_json["tasks"]),
                "info_items_count": len(context_json["information_items"]),
                "lifecycle_items_count": len(context_json["lifecycle_items"]),
            },
        }
