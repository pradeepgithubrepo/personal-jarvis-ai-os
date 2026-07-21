"""
src/agents/financial/financial_agent.py

Financial Agent V1 — Trusted Ledger Builder.

Processes PENDING signal_routes for financial_agent, applies the full
deterministic pipeline, and writes clean records to financial_transactions.

Pipeline (all deterministic except merchant Stage 2):
    signal_routes (PENDING)
        ↓  JOIN  understood_signals  →  contract_json
        ↓  JOIN  qualified_signals   →  raw message
        ↓
    [Stage 1] Spam Filter       — drop UNKNOWN transaction_type + keyword guard
    [Stage 2] canonical_hash    — SHA256 Tier 1 (ref number) or Tier 2 (amount+date+direction+account)
    [Stage 3] Duplicate Check   — lookup canonical_hash; promote if higher-precedence source
    [Stage 4] Transfer Detection— HDFC↔SBI keyword + owner name + double-entry offset
    [Stage 5] Merchant Normalizer — canonicalize() → rule lookup → LLM Stage 2 (optional)
        ↓
    financial_transactions  (INSERT or UPDATE)
    transaction_evidence    (INSERT one row per source signal)
    signal_routes           (UPDATE route_status → COMPLETED / FAILED)

Source Precedence: BANK_STATEMENT_PDF > GPAY_PDF > SMS
LLM Usage: Stage 2 merchant normalization ONLY.

Owner: Financial Agent
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any

from loguru import logger

from src.agents.stubs.base_agent_stub import BaseAgentStub, AgentResult

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

# Source precedence: higher index = higher authority
SOURCE_PRECEDENCE = {"SMS": 1, "GPAY_PDF": 2, "BANK_STATEMENT_PDF": 3}

# Confidence scores per source combination (see PHASE1_IMPLEMENTATION_PLAN.md §4)
CONFIDENCE_MAP = {
    "BANK_STATEMENT_PDF": 100,
    "GPAY_PDF": 90,
    "SMS_WITH_REF": 75,
    "SMS_NO_REF": 60,
}

# Keywords that mark a message as a promotional/spam financial signal (not a real transaction)
SPAM_KEYWORDS = [
    "lifetime free", "credit limit", "pre-approved", "pre approved",
    "loan offer", "eligible for", "apply now", "click here",
    "cashback offer", "reward points", "refer and earn",
    "fd rate", "special offer", "limited time", "get upto",
    "zero annual fee", "upgrade your card", "activate your",
    "congratulations", "you are eligible",
]

# Keywords that conclusively indicate a real transaction (allow-list guard)
REAL_TRANSACTION_KEYWORDS = [
    "debited", "credited", "sent rs", "received rs", "transferred",
    "payment of rs", "paid rs", "withdrawn", "deposited",
    "upi ref", "imps ref", "neft ref", "txn id", "transaction id",
    "your a/c", "your account",
]

# Internal transfer detection: narration keywords
TRANSFER_NARRATION_KEYWORDS = [
    "hdfc to sbi", "sbi to hdfc", "transfer to sbi", "transfer to hdfc",
    "self transfer", "own a/c", "tfr from own", "own account",
    "transfer to self",
]

# Owner names for transfer detection (double-entry offset match)
OWNER_NAMES = [
    "pradeep", "panneerselvam", "pradeep p", "shobana",
]

# Refund/Reversal keywords
REVERSAL_KEYWORDS = [
    "refund", "reversal", "chargeback", "failed upi", "upi failed",
    "return", "reversed", "auto reversal",
]

# Merchant canonicalize: strip these tokens before lookup
STRIP_TOKENS = {
    "LTD", "PVT", "LIMITED", "PRIVATE", "BANGALORE", "CHENNAI",
    "MUMBAI", "DELHI", "HYDERABAD", "KOLKATA", "PUNE", "ONLINE",
    "INSTAMART", "FOODS", "TECH", "SERVICES", "INDIA", "IN", "CO",
    "TECHNOLOGIES", "SOLUTIONS", "DIGITAL", "PAY", "PAYMENTS",
}


# ─────────────────────────────────────────────────────────────────────────────
# FinancialAgent
# ─────────────────────────────────────────────────────────────────────────────

class FinancialAgent(BaseAgentStub):
    """
    Financial Agent V1 — Trusted Ledger Builder.

    Processes PENDING financial_agent routes from signal_routes and writes
    deduplicated, normalized, classified transactions to financial_transactions.
    """

    def __init__(self, provider: str = None, model: str = None):
        self.provider = provider
        self.model = model
        self._llm_client = None  # Lazy-loaded only when Stage 2 merchant normalizer is needed

    @property
    def agent_name(self) -> str:
        return "financial_agent"

    def process(self, contract: dict) -> AgentResult:
        """
        Synchronous stub required by BaseAgentStub interface.
        Dispatch layer writes PENDING route pointers; actual ingestion
        happens asynchronously via process_pending_routes().
        """
        summary = contract.get("summary", "")
        logger.info(f"financial_agent: process() called | summary={summary!r}")
        return AgentResult(
            agent_name=self.agent_name,
            status="STUB_ACCEPTED",
            message="Financial Agent registered route decision. Awaiting pull processing.",
            output={"summary": summary},
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Main Pull Worker
    # ─────────────────────────────────────────────────────────────────────────

    def process_pending_routes(self, supabase_client: Any, routes_to_process: list[dict] = None) -> None:
        """
        Query PENDING routes for financial_agent, run the full 5-stage pipeline,
        and write results to financial_transactions + transaction_evidence.
        """
        if supabase_client is None:
            logger.error("financial_agent: Supabase client required.")
            return

        if routes_to_process is not None:
            pending_routes = routes_to_process
            logger.info(f"financial_agent: Processing {len(pending_routes)} override route(s)...")
        else:
            logger.info("financial_agent: Fetching pending signal routes...")
            try:
                routes_res = (
                    supabase_client
                    .table("signal_routes")
                    .select("id, understood_signal_id, route_reason, route_confidence")
                    .eq("agent_name", "financial_agent")
                    .eq("route_status", "PENDING")
                    .execute()
                )
                pending_routes = routes_res.data or []
                logger.info(f"financial_agent: Found {len(pending_routes)} pending route(s).")
            except Exception as e:
                logger.error(f"financial_agent: Failed to fetch pending routes: {e}")
                return

        if not pending_routes:
            return

        processed = 0
        spam_filtered = 0
        deduped = 0
        promoted = 0
        failed = 0

        for route in pending_routes:
            route_id = route["id"]
            us_id = route["understood_signal_id"]
            logger.info(f"financial_agent: Processing route {route_id} (signal {us_id})...")

            try:
                # ── Fetch understood_signal + qualified_signal (raw message and structured columns) ──
                us_res = (
                    supabase_client
                    .table("understood_signals")
                    .select("id, summary, contract_json, qualified_signal_id, qualified_signals(message, source, amount, currency, transaction_type, metadata, timestamp)")
                    .eq("id", us_id)
                    .limit(1)
                    .execute()
                )
                if not us_res.data:
                    raise ValueError(f"Understood signal {us_id} not found.")

                us_record = us_res.data[0]
                contract = us_record.get("contract_json") or {}
                qs = us_record.get("qualified_signals") or {}
                qs_id = us_record.get("qualified_signal_id")
                raw_message = qs.get("message") or us_record.get("summary") or ""

                qs_source = (qs.get("source") or "").lower()

                if qs_source in ("gpay", "bank_statement"):
                    # Prioritize structured data from qualified_signals
                    source_channel = "GPAY_PDF" if qs_source == "gpay" else "BANK_STATEMENT_PDF"
                    amount = qs.get("amount")
                    currency = qs.get("currency") or "INR"
                    transaction_type_raw = qs.get("transaction_type") or "UNKNOWN"
                    direction_raw = transaction_type_raw

                    # Look up structured metadata
                    source_metadata = (qs.get("metadata") or {}).get("source_metadata") or {}
                    reference_number = source_metadata.get("reference_number")
                    event_date_raw = source_metadata.get("transaction_date")
                    counterparty_hint = source_metadata.get("counterparty") or source_metadata.get("merchant") or ""
                    raw_narration = source_metadata.get("description") or raw_message
                    import_source = source_metadata.get("source_file_name") or source_channel
                    source_account = source_metadata.get("source_account") or _infer_account(raw_message)
                else:
                    # Fallback to LLM / contract_json parsing for SMS / WhatsApp
                    source_channel = "SMS"
                    amount = (
                        contract.get("amount")
                        or (contract.get("type_specific") or {}).get("amount")
                    )
                    currency = (
                        contract.get("currency")
                        or (contract.get("type_specific") or {}).get("currency", "INR")
                        or "INR"
                    )
                    transaction_type_raw = (
                        contract.get("transaction_type")
                        or (contract.get("type_specific") or {}).get("transaction_type")
                        or "UNKNOWN"
                    )
                    direction_raw = (
                        contract.get("direction")
                        or (contract.get("type_specific") or {}).get("direction")
                        or _infer_direction(transaction_type_raw)
                    )
                    event_date_raw = (
                        contract.get("event_date")
                        or contract.get("transaction_date")   # PDF normalizer key
                        or (contract.get("type_specific") or {}).get("event_date")
                    )
                    reference_number = (
                        contract.get("reference_number")
                        or contract.get("transaction_id")
                        or (contract.get("type_specific") or {}).get("reference_number")
                        or (contract.get("type_specific") or {}).get("upi_ref")
                    )
                    source_account = (
                        (contract.get("type_specific") or {}).get("source_account")
                        or _infer_account(raw_message)
                    )
                    raw_narration = (
                        contract.get("description")           # PDF normalizer key
                        or (contract.get("type_specific") or {}).get("narration")
                        or raw_message
                    )
                    counterparty_hint = (
                        contract.get("counterparty")
                        or contract.get("merchant")
                        or (contract.get("type_specific") or {}).get("counterparty")
                        or (contract.get("type_specific") or {}).get("merchant")
                        or ""
                    )
                    # For SMS, check metadata or default
                    source_metadata = (qs.get("metadata") or {}).get("source_metadata") or {}
                    import_source = source_metadata.get("source_file_name") or "SMS"
                    if not event_date_raw:
                        event_date_raw = qs.get("timestamp")

                # ─────────────────────────────────────────────────────────────
                # STAGE 1: Spam Filter
                # ─────────────────────────────────────────────────────────────
                is_spam = self._is_spam(transaction_type_raw, raw_message)
                if is_spam:
                    logger.info(f"financial_agent: Route {route_id} SPAM-FILTERED (tx_type={transaction_type_raw!r})")
                    self._update_route_status(supabase_client, route_id, "COMPLETED",
                                              error_message="SPAM_FILTERED: non-transactional signal")
                    spam_filtered += 1
                    continue

                # Validate required fields
                # amount=None means SUA couldn't parse the amount → treat as unprocessable spam
                if not amount:
                    logger.info(f"financial_agent: Route {route_id} SKIPPED — amount=None (SUA parse failure)")
                    self._update_route_status(supabase_client, route_id, "COMPLETED",
                                              error_message="SKIPPED: amount could not be parsed by SUA")
                    spam_filtered += 1
                    continue
                # event_date=None → use today as fallback (better than failing)
                if not event_date_raw:
                    from datetime import date
                    event_date_raw = date.today().isoformat()
                    logger.warning(f"financial_agent: Route {route_id} — event_date missing, defaulting to today")

                amount_f = float(amount)
                if amount_f <= 0:
                    raise ValueError(f"Invalid amount: {amount_f}")

                event_date = _parse_date(event_date_raw)
                direction = _normalize_direction(direction_raw, transaction_type_raw)

                # ─────────────────────────────────────────────────────────────
                # STAGE 2: canonical_hash generation
                # ─────────────────────────────────────────────────────────────
                canonical_hash = _build_canonical_hash(
                    amount=amount_f,
                    event_date=event_date,
                    direction=direction,
                    source_account=source_account,
                    reference_number=reference_number,
                )

                # ─────────────────────────────────────────────────────────────
                # STAGE 3: Duplicate Detection + Source Promotion
                # ─────────────────────────────────────────────────────────────
                existing = self._find_existing(supabase_client, canonical_hash)

                if existing:
                    existing_source = existing.get("source", "SMS")
                    existing_id = existing.get("transaction_id")
                    incoming_precedence = SOURCE_PRECEDENCE.get(source_channel, 1)
                    existing_precedence = SOURCE_PRECEDENCE.get(existing_source, 1)

                    # Write evidence regardless
                    self._write_evidence(
                        supabase_client, existing_id, source_channel,
                        route_id, us_id, qs_id, amount_f, raw_narration, reference_number
                    )

                    if incoming_precedence > existing_precedence:
                        # Promote: higher-authority source wins
                        confidence = _score_confidence(source_channel, reference_number)
                        supabase_client.table("financial_transactions").update({
                            "source": source_channel,
                            "import_source": import_source,
                            "confidence_score": confidence,
                            "settlement_status": "SETTLED",
                            "signal_route_id": route_id,
                            "updated_at": _now(),
                        }).eq("transaction_id", existing_id).execute()
                        logger.info(f"financial_agent: Route {route_id} PROMOTED existing {existing_id} "
                                    f"({existing_source} → {source_channel})")
                        promoted += 1
                    else:
                        logger.info(f"financial_agent: Route {route_id} DUPLICATE of {existing_id} "
                                    f"({source_channel} ≤ {existing_source}) — evidence recorded only")
                        deduped += 1

                    self._update_route_status(supabase_client, route_id, "COMPLETED")
                    continue

                # ─────────────────────────────────────────────────────────────
                # STAGE 4: Internal Transfer Detection
                # ─────────────────────────────────────────────────────────────
                is_self_transfer = self._detect_transfer(raw_narration, supabase_client, amount_f, direction, event_date)

                # ─────────────────────────────────────────────────────────────
                # STAGE 5: Merchant Normalization
                # ─────────────────────────────────────────────────────────────
                counterparty = counterparty_hint
                merchant, category = self._normalize_merchant(supabase_client, counterparty, raw_narration)

                # Infer subcategory and potentially override category
                subcategory, category = self._infer_subcategory(merchant, category, raw_narration)

                # Classify transaction type
                tx_type = _classify_transaction_type(
                    direction=direction,
                    is_self_transfer=is_self_transfer,
                    raw_narration=raw_narration,
                    category=category,
                    transaction_type_raw=transaction_type_raw,
                )

                # Confidence + settlement
                confidence = _score_confidence(source_channel, reference_number)
                settlement = "SETTLED" if source_channel in ("BANK_STATEMENT_PDF", "GPAY_PDF") else "PENDING"

                # ─────────────────────────────────────────────────────────────
                # WRITE: financial_transactions
                # ─────────────────────────────────────────────────────────────
                ledger_row = {
                    "canonical_hash": canonical_hash,
                    "event_date": event_date,
                    "amount": amount_f,
                    "currency": currency,
                    "direction": direction,
                    "transaction_type": tx_type,
                    "source": source_channel,
                    "import_source": import_source,
                    "confidence_score": confidence,
                    "settlement_status": settlement,
                    "raw_narration": raw_narration[:500] if raw_narration else None,
                    "reference_number": reference_number,
                    "merchant": merchant,
                    "counterparty": counterparty[:150] if counterparty else None,
                    "category": category,
                    "subcategory": subcategory,
                    "source_account": source_account,
                    "is_self_transfer": is_self_transfer,
                    "is_override": False,
                    "signal_route_id": route_id,
                    "created_at": _now(),
                    "updated_at": _now(),
                }
                
                try:
                    ins_res = supabase_client.table("financial_transactions").insert(ledger_row).execute()
                except Exception as e:
                    err_msg = str(e)
                    if "column" in err_msg.lower() and "subcategory" in err_msg.lower():
                        logger.warning("financial_agent: subcategory column not found in database. Falling back to insert without subcategory.")
                        ledger_row.pop("subcategory", None)
                        ins_res = supabase_client.table("financial_transactions").insert(ledger_row).execute()
                    else:
                        raise

                if not ins_res.data:
                    raise ValueError("Insert to financial_transactions returned no data.")

                new_tx_id = ins_res.data[0]["transaction_id"]
                logger.info(f"financial_agent: Created transaction {new_tx_id} "
                            f"| {direction} Rs.{amount_f} | {merchant or 'Unknown'} | {tx_type}")

                # ─────────────────────────────────────────────────────────────
                # WRITE: transaction_evidence (first source)
                # ─────────────────────────────────────────────────────────────
                self._write_evidence(
                    supabase_client, new_tx_id, source_channel,
                    route_id, us_id, qs_id, amount_f, raw_narration, reference_number
                )

                # ─────────────────────────────────────────────────────────────
                # UPDATE: signal_routes → COMPLETED
                # ─────────────────────────────────────────────────────────────
                self._update_route_status(supabase_client, route_id, "COMPLETED")
                processed += 1

            except Exception as e:
                logger.error(f"financial_agent: Failed to process route {route_id}: {e}")
                self._update_route_status(supabase_client, route_id, "FAILED", error_message=str(e))
                failed += 1

        logger.info(
            f"financial_agent: Done — "
            f"processed={processed} | spam_filtered={spam_filtered} | "
            f"deduped={deduped} | promoted={promoted} | failed={failed}"
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Stage Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _is_spam(self, transaction_type: str, raw_message: str) -> bool:
        """
        Stage 1: Spam filter.
        Returns True if the signal is a marketing/promotional message (not a real transaction).
        """
        msg_lower = raw_message.lower()
        # Ignore UPI Lite amount load/top-up transactions (with hyphens or spaces, e.g. UPI-LITE-...-ADD MONEY)
        has_upi_lite = "upi lite" in msg_lower or "upi-lite" in msg_lower
        is_load = "add money" in msg_lower or "top-up" in msg_lower or "top up" in msg_lower or "load" in msg_lower
        if has_upi_lite and is_load:
            return True

        # Primary gate: contract_json classified it as UNKNOWN
        if transaction_type == "UNKNOWN":
            # Secondary guard: check if ANY real transaction keyword is present
            # (catches cases where SUA misclassified but the message is clearly real)
            has_real_signal = any(kw in msg_lower for kw in REAL_TRANSACTION_KEYWORDS)
            if not has_real_signal:
                return True  # No real transaction signal found → spam

        # Spam keyword gate (even if transaction_type is set, block known spam phrases)
        if any(kw in msg_lower for kw in SPAM_KEYWORDS):
            return True

        return False

    def _find_existing(self, supabase_client: Any, canonical_hash: str) -> dict | None:
        """
        Stage 3: Look up canonical_hash in the ledger.
        Returns existing row dict or None.
        """
        try:
            res = (
                supabase_client
                .table("financial_transactions")
                .select("transaction_id, source, confidence_score, settlement_status")
                .eq("canonical_hash", canonical_hash)
                .limit(1)
                .execute()
            )
            return res.data[0] if res.data else None
        except Exception as e:
            logger.warning(f"financial_agent: canonical_hash lookup failed: {e}")
            return None

    def _detect_transfer(
        self, raw_narration: str, supabase_client: Any,
        amount: float, direction: str, event_date: str
    ) -> bool:
        """
        Stage 4: Internal transfer detection.
        Rule 1: Narration contains transfer keywords.
        Rule 2: Counterparty matches owner names.
        Rule 3: Offsetting double-entry exists within 1 hour.
        """
        narr_lower = raw_narration.lower() if raw_narration else ""

        # Rule 1: explicit transfer keyword
        if any(kw in narr_lower for kw in TRANSFER_NARRATION_KEYWORDS):
            logger.debug(f"financial_agent: Transfer detected via Rule 1 (keyword)")
            return True

        # Rule 2: owner name in narration
        if any(name in narr_lower for name in OWNER_NAMES):
            logger.debug(f"financial_agent: Transfer detected via Rule 2 (owner name)")
            return True

        # Rule 3: double-entry offset (same amount, opposite direction, same date)
        try:
            opposite = "CREDIT" if direction == "DEBIT" else "DEBIT"
            res = (
                supabase_client
                .table("financial_transactions")
                .select("transaction_id")
                .eq("amount", amount)
                .eq("direction", opposite)
                .eq("event_date", event_date)
                .eq("is_self_transfer", False)
                .limit(1)
                .execute()
            )
            if res.data:
                # Mark the matched counterpart as self-transfer too
                matched_id = res.data[0]["transaction_id"]
                supabase_client.table("financial_transactions").update({
                    "is_self_transfer": True,
                    "transaction_type": "TRANSFER",
                    "updated_at": _now(),
                }).eq("transaction_id", matched_id).execute()
                logger.debug(f"financial_agent: Transfer detected via Rule 3 (double-entry offset) — matched {matched_id}")
                return True
        except Exception as e:
            logger.warning(f"financial_agent: Double-entry offset check failed: {e}")

        return False

    def _normalize_merchant(
        self, supabase_client: Any, counterparty: str, raw_narration: str
    ) -> tuple[str | None, str | None]:
        """
        Stage 5: Merchant normalization.
        Lookup order: EXACT → CANONICAL → CONTAINS → LLM Stage 2.
        Returns (normalized_merchant, category).
        """
        raw = counterparty or raw_narration or ""
        if not raw.strip():
            return None, None

        canonical = _canonicalize(raw)

        try:
            # Stage 1a: EXACT match on canonical_key
            res = (
                supabase_client
                .table("merchant_normalization_rules")
                .select("normalized_merchant, category_override")
                .eq("canonical_key", canonical)
                .limit(1)
                .execute()
            )
            if res.data:
                r = res.data[0]
                return r["normalized_merchant"], r.get("category_override")

            # Stage 1b: CONTAINS match — scan for substring
            rules_res = (
                supabase_client
                .table("merchant_normalization_rules")
                .select("canonical_key, normalized_merchant, category_override, match_type")
                .eq("match_type", "CONTAINS")
                .execute()
            )
            for rule in (rules_res.data or []):
                if rule["canonical_key"].upper() in canonical.upper():
                    return rule["normalized_merchant"], rule.get("category_override")

        except Exception as e:
            logger.warning(f"financial_agent: Merchant rule lookup failed: {e}")

        # Stage 2: LLM (optional, lazy-loaded) — skip if client unavailable
        try:
            llm = self._get_llm_client()
            if llm:
                merchant, category = self._llm_merchant_normalize(llm, raw, canonical)
                if merchant:
                    # Cache the result for future use
                    self._cache_merchant_rule(supabase_client, canonical, raw, merchant, category)
                    return merchant, category
        except Exception as e:
            logger.warning(f"financial_agent: LLM merchant normalization failed: {e}")

        # Fallback: return the canonical string as-is
        return canonical.title() if canonical else None, None

    def _llm_merchant_normalize(self, llm: Any, raw: str, canonical: str) -> tuple[str | None, str | None]:
        """LLM Stage 2: Ask LLM to normalize merchant and suggest category."""
        prompt = f"""You are a financial transaction merchant normalizer.

Raw merchant string: "{raw}"
Canonical key (geographic/legal tokens stripped): "{canonical}"

Task:
1. Provide a clean, human-readable merchant name (e.g. "Swiggy", "Apollo Pharmacy", "HDFC Bank").
2. Suggest a category from this list ONLY: Food, Shopping, Transport, Health, Utilities, Entertainment, Banking, Insurance, Investment, Education, Fuel, Dining, Travel, Other.

Return ONLY a JSON object, no explanation, no markdown:
{{"merchant": "Clean Name", "category": "Category"}}"""

        try:
            raw_response = llm.ask(prompt)
            clean = raw_response.replace("```json", "").replace("```", "").strip()
            import json
            parsed = json.loads(clean)
            return parsed.get("merchant"), parsed.get("category")
        except Exception:
            return None, None

    def _cache_merchant_rule(
        self, supabase_client: Any, canonical_key: str, raw_example: str,
        normalized_merchant: str, category: str | None
    ) -> None:
        """Cache a new merchant normalization rule (LLM result, not user-approved)."""
        try:
            supabase_client.table("merchant_normalization_rules").upsert({
                "canonical_key": canonical_key,
                "raw_examples": [raw_example],
                "normalized_merchant": normalized_merchant,
                "category_override": category,
                "match_type": "CANONICAL",
                "approved_by_user": False,
                "updated_at": _now(),
            }, on_conflict="canonical_key").execute()
        except Exception as e:
            logger.warning(f"financial_agent: Failed to cache merchant rule for {canonical_key!r}: {e}")

    def _get_llm_client(self) -> Any | None:
        """Lazy-load LLM client only when Stage 2 merchant normalization is needed."""
        if self._llm_client is None:
            try:
                from intelligence.llm_client import LLMClient
                self._llm_client = LLMClient(provider=self.provider, model=self.model)
            except Exception as e:
                logger.warning(f"financial_agent: Could not load LLM client: {e}")
        return self._llm_client

    def _write_evidence(
        self, supabase_client: Any, transaction_id: str, source: str,
        route_id: str, understood_signal_id: str, qualified_signal_id: str | None,
        amount_reported: float, raw_narration: str | None, reference_number: str | None
    ) -> None:
        """Write a transaction_evidence row. Never raises — evidence is best-effort."""
        try:
            supabase_client.table("transaction_evidence").insert({
                "transaction_id": transaction_id,
                "source": source,
                "signal_route_id": route_id,
                "understood_signal_id": understood_signal_id,
                "qualified_signal_id": qualified_signal_id,
                "amount_reported": amount_reported,
                "raw_narration": raw_narration[:500] if raw_narration else None,
                "reference_number": reference_number,
                "captured_at": _now(),
            }).execute()
        except Exception as e:
            logger.warning(f"financial_agent: Failed to write evidence for tx {transaction_id}: {e}")

    def _update_route_status(
        self, supabase_client: Any, route_id: str, status: str, error_message: str = None
    ) -> None:
        """Update signal_routes.route_status — mirrors TodoAgent pattern exactly."""
        update_data = {"route_status": status, "completed_at": _now()}
        if error_message:
            update_data["error_message"] = error_message[:1000]
        try:
            supabase_client.table("signal_routes").update(update_data).eq("id", route_id).execute()
            logger.info(f"financial_agent: Route {route_id} → {status}")
        except Exception as e:
            logger.error(f"financial_agent: Failed to update route {route_id} to {status}: {e}")

    def _infer_subcategory(self, merchant: str, category: str, raw_narration: str) -> tuple[str | None, str]:
        """
        Infers subcategory and potentially overrides category based on rules.
        Returns a tuple: (subcategory, category).
        """
        m_lower = (merchant or "").lower()
        n_lower = (raw_narration or "").lower()
        cat_lower = (category or "").lower()

        # Rule 1: JISHA JOHN C - Office Food
        if "jisha john" in m_lower or "jisha john" in n_lower:
            return "Office Food", "Food"

        # Rule 2: Ellammal - Fish
        if "ellammal" in m_lower or "ellammal" in n_lower:
            return "Fish", "Food"

        # Rule 3: Google - Google
        if "google" in m_lower:
            return "Google", "Other"

        # Rule 4: Electricals / Hardware
        hardware_keywords = ["electrical", "hardware", "plywood", "paint", "cement", "sanitary", "timber", "wood", "tiles"]
        if any(kw in m_lower or kw in n_lower for kw in hardware_keywords):
            return "Hardware", "Housing"

        # Other useful subcategories with low cardinality
        if "tangedco" in m_lower or "electricity" in n_lower or "electric bill" in n_lower:
            return "Electricity Bill", "Utilities"
        if "indane" in m_lower or "gas" in n_lower or "lpg" in n_lower:
            return "Gas Bill", "Utilities"
        if "airtel" in m_lower or "jio" in m_lower or "recharge" in n_lower or "mobile bill" in n_lower:
            return "Mobile Recharge", "Utilities"
        if "netflix" in m_lower or "spotify" in m_lower or "prime video" in m_lower or "hotstar" in m_lower or "jiohotstar" in m_lower or "perplexity" in m_lower:
            return "Subscription", "Entertainment"
        if "atm" in m_lower or "atw" in m_lower or "cash withdrawal" in n_lower or "withdrawn" in n_lower:
            return "ATM Withdrawal", "Other"
        if "sbi card" in m_lower or "credit card" in n_lower or "sbi card" in n_lower or "axis bank credit card" in n_lower:
            return "Credit Card Payment", "Other"
        if "mutual fund" in n_lower or "et money" in m_lower or "nps" in m_lower or "icici mutual" in m_lower or "investment" in n_lower or "gold loan" in n_lower:
            return "Investment", "Investment"
        
        # Check for cab/auto transport (ola, uber, rapido)
        is_cab_ride = False
        if "uber" in m_lower or "ola" in m_lower or "rapido" in m_lower:
            is_cab_ride = True
        elif "cab" in n_lower:
            is_cab_ride = True
        elif re.search(r"\bauto\b", n_lower):
            # standalone "auto" word check
            # Exclude auto pay, auto debit, auto sweep
            if not any(kw in n_lower for kw in ["auto pay", "autopay", "auto-pay", "auto debit", "autodebit", "auto-debit", "auto sweep", "autosweep", "auto-sweep"]):
                is_cab_ride = True
        
        if is_cab_ride:
            return "Cab / Auto", "Transport"

        if "petrol" in n_lower or "diesel" in n_lower or "shell" in m_lower or "hpcl" in m_lower or "bpcl" in m_lower or "fuel" in n_lower:
            return "Fuel", "Transport"
        if "irctc" in m_lower or "flight" in n_lower or "indigo" in m_lower or "redbus" in m_lower:
            return "Travel Booking", "Travel"
        if "salary" in n_lower or "salary" in m_lower:
            return "Salary", "Other"

        return None, category


# ─────────────────────────────────────────────────────────────────────────────
# Pure Functions (deterministic, no I/O)
# ─────────────────────────────────────────────────────────────────────────────

def _canonicalize(raw: str) -> str:
    """
    Strip geographic and legal noise tokens from a merchant string.
    Example: 'SWIGGY*BANGALORE LTD' → 'SWIGGY'
    """
    tokens = raw.upper().replace("*", " ").replace("-", " ").split()
    cleaned = [t for t in tokens if t not in STRIP_TOKENS and len(t) > 1]
    return " ".join(cleaned).strip()


def _build_canonical_hash(
    amount: float,
    event_date: str,
    direction: str,
    source_account: str | None,
    reference_number: str | None,
) -> str:
    """
    Build a deterministic SHA256 deduplication hash.
    Tier 1: reference_number present → hash(reference_number)
    Tier 2: fallback → hash(amount + date + direction + source_account)
    """
    if reference_number and reference_number.strip():
        raw = reference_number.strip().upper()
    else:
        date_key = event_date[:10] if event_date else "UNKNOWN"  # YYYY-MM-DD only
        account_key = (source_account or "UNKNOWN").upper()
        raw = f"{amount:.2f}|{date_key}|{direction}|{account_key}"

    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _score_confidence(source: str, reference_number: str | None) -> int:
    """Return confidence score based on source and whether a reference number exists."""
    if source == "BANK_STATEMENT_PDF":
        return 100
    if source == "GPAY_PDF":
        return 90
    if source == "SMS":
        return 75 if (reference_number and reference_number.strip()) else 60
    return 60


def _infer_source(contract: dict, raw_message: str) -> str:
    """Infer the source channel from contract metadata or raw message content."""
    source_hint = (contract.get("source") or "").upper()
    if "STATEMENT" in source_hint or "BANK" in source_hint:
        return "BANK_STATEMENT_PDF"
    if "GPAY" in source_hint or "GOOGLE PAY" in source_hint:
        return "GPAY_PDF"
    # Check raw message for PDF-sourced signals
    msg = raw_message.lower()
    if "google pay" in msg or "gpay" in msg:
        return "GPAY_PDF"
    return "SMS"


def _infer_account(raw_message: str) -> str | None:
    """Infer source bank account from raw message text."""
    msg = raw_message.upper()
    if "HDFC" in msg:
        return "HDFC"
    if "SBI" in msg or "STATE BANK" in msg:
        return "SBI"
    if "ICICI" in msg:
        return "ICICI"
    if "AXIS" in msg:
        return "AXIS"
    return None


def _infer_direction(transaction_type: str) -> str:
    """Infer DEBIT/CREDIT from transaction_type string."""
    tt = transaction_type.upper()
    if tt in ("DEBIT", "PAYMENT", "SENT", "WITHDRAWN", "PURCHASE"):
        return "DEBIT"
    if tt in ("CREDIT", "RECEIVED", "DEPOSITED", "REFUND"):
        return "CREDIT"
    return "DEBIT"  # Conservative default


def _normalize_direction(direction_raw: str, transaction_type: str) -> str:
    """Normalize direction value to DEBIT or CREDIT."""
    d = (direction_raw or "").upper().strip()
    if d in ("DEBIT", "DR"):
        return "DEBIT"
    if d in ("CREDIT", "CR"):
        return "CREDIT"
    return _infer_direction(transaction_type)


def _classify_transaction_type(
    direction: str,
    is_self_transfer: bool,
    raw_narration: str,
    category: str | None,
    transaction_type_raw: str,
) -> str:
    """
    Map a transaction to one of the 10 canonical types.
    All deterministic — no LLM.
    """
    if is_self_transfer:
        return "TRANSFER"

    narr = (raw_narration or "").lower()

    # Refund / Reversal detection (takes precedence over direction)
    if any(kw in narr for kw in REVERSAL_KEYWORDS):
        if "refund" in narr or "return" in narr:
            return "REFUND"
        return "REVERSAL"

    # Category-based classification (from merchant normalizer)
    cat = (category or "").lower()
    if cat == "investment":
        return "INVESTMENT"

    # Fee / Interest / Tax detection from narration
    if any(kw in narr for kw in ["annual fee", "processing fee", "service charge", "atm charge", "bank charge"]):
        return "FEE"
    if any(kw in narr for kw in ["interest credit", "interest debit", "fd interest", "savings interest"]):
        return "INTEREST"
    if any(kw in narr for kw in ["tds", "tax deducted", "gst", "advance tax"]):
        return "TAX"

    # Default by direction
    if direction == "DEBIT":
        return "EXPENSE"
    if direction == "CREDIT":
        return "INCOME"

    return "OTHER"


def _parse_date(event_date_raw: str) -> str:
    """
    Parse event_date to YYYY-MM-DD string (date only, no time).
    Accepts ISO timestamps, DD/MM/YYYY, DD-MM-YYYY, etc.
    """
    if not event_date_raw:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Already ISO date
    if re.match(r"^\d{4}-\d{2}-\d{2}", event_date_raw):
        return event_date_raw[:10]

    # DD/MM/YYYY or DD-MM-YYYY
    m = re.match(r"^(\d{2})[/\-](\d{2})[/\-](\d{4})", event_date_raw)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"

    # Fallback
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
