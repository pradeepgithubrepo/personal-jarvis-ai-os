# services/financial_aggregator.py
# Financial Agent V2 — Full Revision
#
# Ownership model:
#   FinancialAggregator  → fact production  (transfer detection, classification,
#                          salary detection, refund processing)
#   AggregationService   → rollup computation (spending summaries, category
#                          spends, MoM trends) — idempotent, safe to re-run
#
# V2 Changes implemented:
#   1. 4-condition internal transfer detection (amount + account ownership +
#      transfer indicator + typed time window)
#   2. 4-tier salary detection algorithm
#   3. Split Accounting Spend vs Lifestyle Spend
#   4. Refund offsets prior spending — never inflates income
#   5. (Pre-seeded merchant registry lives in FinancialClassifier)
#   6. AggregationService class owns all rollup writes

import uuid
from datetime import datetime, timedelta
from loguru import logger
from services.supabase_repo import SupabaseRepo, supabase
from services.financial_classifier import FinancialClassifier


# ---------------------------------------------------------------------------
# Transfer type → max detection window (seconds)
# ---------------------------------------------------------------------------
TRANSFER_WINDOWS: dict[str, int] = {
    "IMPS":       30 * 60,           #  30 minutes
    "UPI":        10 * 60,           #  10 minutes
    "NEFT":       4 * 60 * 60,       #   4 hours
    "RTGS":       2 * 60 * 60,       #   2 hours
    "YONO":       48 * 60 * 60,      #  48 hours
    "NETBANKING": 48 * 60 * 60,      #  48 hours
    "UNKNOWN":    48 * 60 * 60,      #  48 hours (default)
}

# Condition 3 — transfer indicator keywords → transfer type
TRANSFER_INDICATORS: list[tuple[str, str]] = [
    ("imps",              "IMPS"),
    ("neft",              "NEFT"),
    ("rtgs",              "RTGS"),
    ("upi transfer",      "UPI"),
    ("fund transfer",     "UPI"),
    ("transfer to",       "UPI"),
    ("transfer from",     "UPI"),
    ("moved to",          "UPI"),
    ("a/c credited",      "UPI"),
    ("yono",              "YONO"),
    ("net banking transfer", "NETBANKING"),
    ("online transfer",   "NETBANKING"),
]

# Condition 2 — known account ownership aliases (sender/receiver strings)
# These resolve to the user's own registered bank accounts.
# In the absence of a `bank_account` Supabase table, this list is the
# in-process equivalent.
KNOWN_ACCOUNT_ALIASES: set[str] = {
    # HDFC
    "hdfc", "hdfcbk", "hdfcbank", "jm-hdfcbk-s", "cp-hdfcbk-s",
    # SBI
    "sbi", "sbipsg", "ad-sbipsg-t", "yono",
    # ICICI
    "icici", "icicibank",
    # Axis
    "axis", "axisbank",
    # Kotak
    "kotak", "kotakbank",
    # IndusInd
    "indusind",
    # Generic transfer strings found in Indian bank SMS
    "bank transfer", "netbanking", "net banking",
}

# Tier-1 salary keywords
SALARY_KEYWORDS: list[str] = [
    "salary", "sal cr", "sal credit", "monthly salary",
    "basic pay", "net pay", "emoluments", "payroll",
]

# Tier-4 large credit threshold (INR)
LARGE_CREDIT_THRESHOLD = 20_000.0

# Refund matching window (days)
REFUND_MATCH_WINDOW_DAYS = 30


# =============================================================================
# Helpers
# =============================================================================

def _parse_dt(dt_str: str | None) -> datetime | None:
    """Parse ISO datetime string (with or without Z / microseconds) → datetime."""
    if not dt_str:
        return None
    try:
        clean = dt_str.replace("Z", "").split(".")[0]
        return datetime.fromisoformat(clean)
    except Exception:
        return None


def _month_key(dt: datetime) -> str:
    """Return YYYY-MM string for a datetime."""
    return dt.strftime("%Y-%m")


def _detect_transfer_type(text: str) -> tuple[str, int]:
    """
    Scan lowercased text for a transfer indicator keyword.
    Returns (transfer_type, window_seconds).
    """
    for keyword, ttype in TRANSFER_INDICATORS:
        if keyword in text:
            return ttype, TRANSFER_WINDOWS[ttype]
    return "UNKNOWN", TRANSFER_WINDOWS["UNKNOWN"]


def _has_account_ownership(text: str) -> bool:
    """Return True if any known account alias appears in the lowercased text."""
    for alias in KNOWN_ACCOUNT_ALIASES:
        if alias in text:
            return True
    return False


def _categorise_credit(message: str) -> str:
    """
    Determine the sub-type of a credit event from its message.
    Returns: 'SALARY', 'REFUND', 'CREDIT', or 'UNKNOWN'.
    """
    m = message.lower()
    # Refund patterns (must check before 'salary' to avoid mis-match)
    if any(k in m for k in ["refund", "refunded", "reversed", "reversal",
                              "credited back", "adjusted against"]):
        return "REFUND"
    # Salary patterns
    if any(k in m for k in SALARY_KEYWORDS):
        return "SALARY"
    # Generic credited / deposit
    if any(k in m for k in ["credited", "received", "deposit", "credit alert",
                              "amount credited", "amount received"]):
        return "CREDIT"
    return "UNKNOWN"


# =============================================================================
# FinancialAggregator — Fact Production
# =============================================================================

class FinancialAggregator:
    """
    Owns fact production for the Financial Agent pipeline.

    Responsibilities:
      - Internal transfer detection (4-condition algorithm)
      - Transaction classification (FinancialClassifier)
      - Salary event detection (4-tier algorithm)
      - Refund event processing (offsets prior spending)

    Does NOT own rollup tables — that is AggregationService.
    """

    @classmethod
    def run_aggregation(cls) -> None:
        """
        Entry point for the Financial Aggregation pipeline.

        1. Fetch all financial events from Supabase.
        2. Build enriched event list (parse timestamps, classify credit type).
        3. Clear existing summary tables (idempotent rebuild).
        4. Run 4-condition internal transfer detection.
        5. Run 4-tier salary detection on credit events.
        6. Classify remaining debit events.
        7. Process refund events (apply spending offsets).
        8. Delegate rollup computation to AggregationService.
        """
        logger.info("╔══════════════════════════════════════════╗")
        logger.info("║  Financial Aggregator V2 — Starting      ║")
        logger.info("╚══════════════════════════════════════════╝")

        events = SupabaseRepo.fetch_financial_events()
        if not events:
            logger.warning("No financial events found in Supabase. Aggregation skipped.")
            return

        # Fetch signal messages for enrichment
        signal_messages = cls._fetch_signal_messages()

        # Enrich each event with parsed fields
        enriched = cls._enrich_events(events, signal_messages)

        # Clear summary tables for clean idempotent rebuild
        SupabaseRepo.clear_summary_tables()

        # ── Step 1: Internal Transfer Detection (4-condition) ─────────────────
        internal_transfer_ids = cls.detect_internal_transfers(enriched)
        logger.info(f"  ✓ Internal transfers detected: {len(internal_transfer_ids) // 2} pairs "
                    f"({len(internal_transfer_ids)} legs)")

        # ── Step 2: Salary Detection (4-tier) ────────────────────────────────
        salary_event_ids = cls.detect_salary_events(enriched, internal_transfer_ids)
        logger.info(f"  ✓ Salary events detected: {len(salary_event_ids)}")

        # ── Step 3: Classify debit transactions ──────────────────────────────
        cls.classify_transactions(enriched, internal_transfer_ids)

        # ── Step 4: Process refund events ────────────────────────────────────
        refund_offsets_by_month = cls.process_refund_events(enriched, internal_transfer_ids)

        # ── Step 5: Delegate rollups to AggregationService ───────────────────
        AggregationService.run(enriched, internal_transfer_ids, salary_event_ids, refund_offsets_by_month)

        logger.info("╔══════════════════════════════════════════╗")
        logger.info("║  Financial Aggregator V2 — Complete      ║")
        logger.info("╚══════════════════════════════════════════╝")

    # ── Internal helpers ──────────────────────────────────────────────────────

    @classmethod
    def _fetch_signal_messages(cls) -> dict[str, str]:
        """Fetch signal messages keyed by signal_id."""
        try:
            res = supabase.table("signals").select("signal_id, message").execute()
            return {s["signal_id"]: s["message"] for s in (res.data or [])}
        except Exception as e:
            logger.error(f"Failed to fetch signals: {e}")
            return {}

    @classmethod
    def _enrich_events(cls, events: list[dict], signal_messages: dict) -> list[dict]:
        """
        Augment each event dict with:
          - parsed_dt: datetime | None
          - month_key: str | None
          - message: lowercased signal message
          - credit_subtype: 'SALARY' | 'REFUND' | 'CREDIT' | 'UNKNOWN' | None
          - is_credit: bool
          - amount_float: float
        """
        enriched = []
        for e in events:
            sig_id = e.get("source_signal_id")
            message = (signal_messages.get(sig_id) or
                       signal_messages.get(str(sig_id)) or "").lower()

            parsed_dt = _parse_dt(e.get("event_timestamp"))
            mkey = _month_key(parsed_dt) if parsed_dt else None
            amount = float(e.get("amount") or 0.0)

            # Determine credit/debit from message content
            credit_subtype = _categorise_credit(message)
            is_credit = credit_subtype in ("SALARY", "REFUND", "CREDIT")

            item = dict(e)
            item["message"] = message
            item["parsed_dt"] = parsed_dt
            item["month_key"] = mkey
            item["credit_subtype"] = credit_subtype if is_credit else None
            item["is_credit"] = is_credit
            item["amount_float"] = amount
            enriched.append(item)

        return enriched

    # =========================================================================
    # 1. Internal Transfer Detection — 4-Condition Algorithm
    # =========================================================================

    @classmethod
    def detect_internal_transfers(cls, enriched: list[dict]) -> set[str]:
        """
        Detects internal transfer pairs using the V2 4-condition algorithm.

        Condition 1 — Amount match: |D.amount - C.amount| < ₹1
        Condition 2 — Account ownership: both legs resolve to known account aliases
        Condition 3 — Transfer indicator: message contains a transfer keyword
        Condition 4 — Time window: within the typed transfer window

        All four conditions must be satisfied.
        Returns set of event_ids that are internal transfer legs.
        """
        debits = [e for e in enriched if not e["is_credit"] and e["parsed_dt"]]
        credits = [e for e in enriched if e["is_credit"] and e["parsed_dt"]]

        internal_transfer_ids: set[str] = set()

        for d in debits:
            d_id = d.get("financial_event_id")
            if d_id in internal_transfer_ids:
                continue

            d_amount = d["amount_float"]
            d_dt = d["parsed_dt"]
            d_text = (f"{d['message']} {d.get('merchant', '')} "
                      f"{d.get('paid_to', '')} {d.get('paid_from', '')}").lower()

            # Condition 3 — does the debit have a transfer indicator?
            d_transfer_type, d_window = _detect_transfer_type(d_text)
            d_has_indicator = d_transfer_type != "UNKNOWN" or any(
                kw in d_text for kw in ["transfer", "imps", "neft", "rtgs",
                                         "upi", "yono", "netbanking"]
            )
            # Note: we still proceed if transfer type is UNKNOWN but text has
            # generic "transfer" wording — Condition 3 is satisfied.
            if not d_has_indicator:
                continue

            # Condition 2 — debit side has a known account alias?
            if not _has_account_ownership(d_text):
                continue

            for c in credits:
                c_id = c.get("financial_event_id")
                if c_id in internal_transfer_ids:
                    continue

                c_amount = c["amount_float"]
                c_dt = c["parsed_dt"]
                c_text = (f"{c['message']} {c.get('merchant', '')} "
                          f"{c.get('paid_to', '')} {c.get('paid_from', '')}").lower()

                # Condition 1 — amount match within ₹1
                if abs(d_amount - c_amount) >= 1.0:
                    continue

                # Condition 3 (credit side) — transfer indicator present
                c_transfer_type, c_window = _detect_transfer_type(c_text)
                c_has_indicator = c_transfer_type != "UNKNOWN" or any(
                    kw in c_text for kw in ["transfer", "imps", "neft", "rtgs",
                                             "upi", "yono", "netbanking"]
                )
                if not c_has_indicator:
                    continue

                # Condition 2 (credit side) — known account alias
                if not _has_account_ownership(c_text):
                    continue

                # Condition 4 — time window (use the tighter of the two windows)
                effective_window = min(d_window, c_window)
                time_diff = abs((d_dt - c_dt).total_seconds())
                if time_diff > effective_window:
                    continue

                # All 4 conditions satisfied — this is an internal transfer pair
                resolved_type = d_transfer_type if d_transfer_type != "UNKNOWN" else c_transfer_type
                window_secs = effective_window

                internal_transfer_ids.add(d_id)
                internal_transfer_ids.add(c_id)

                # Update categories in Supabase
                SupabaseRepo.reclassify_financial_event(uuid.UUID(d_id), "INTERNAL_TRANSFER")
                SupabaseRepo.reclassify_financial_event(uuid.UUID(c_id), "INTERNAL_TRANSFER")

                # Persist classification records
                for ev_id in (d_id, c_id):
                    cls_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"class-{ev_id}")
                    SupabaseRepo.save_transaction_classification(
                        classification_id=cls_id,
                        financial_event_id=uuid.UUID(ev_id),
                        classification="INTERNAL_TRANSFER",
                        confidence=1.0,
                    )

                # Persist transfer pair record
                pair_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"pair-{d_id}-{c_id}")
                SupabaseRepo.save_transfer_pair(
                    pair_id=pair_id,
                    debit_event_id=d_id,
                    credit_event_id=c_id,
                    amount=d_amount,
                    currency=d.get("currency") or "INR",
                    transfer_type=resolved_type,
                    confidence=1.0,
                    window_used_seconds=window_secs,
                )

                # Update in-memory flags
                d["category"] = "INTERNAL_TRANSFER"
                c["category"] = "INTERNAL_TRANSFER"
                break  # each debit leg matches only one credit leg

        return internal_transfer_ids

    # =========================================================================
    # 2. Salary Detection — 4-Tier Algorithm
    # =========================================================================

    @classmethod
    def detect_salary_events(cls, enriched: list[dict], internal_transfer_ids: set[str]) -> set[str]:
        """
        Runs 4-tier salary detection on credit events.

        Tier 1 (conf 0.95): keyword match → INCOME_SALARY
        Tier 2 (conf 0.90): sender in salary_source registry → INCOME_SALARY
                            (registry is empty at V2 launch; grows from Tier 3 promotions)
        Tier 3 (conf 0.80): recurring same-sender credit ≥ 3 of last 4 months → INCOME_SALARY_CANDIDATE
        Tier 4 (conf 0.50): large unmatched credit ≥ ₹20,000 → INCOME_UNCLASSIFIED

        Returns set of event_ids classified as confirmed salary (Tier 1 + 2).
        """
        credits = [
            e for e in enriched
            if e["is_credit"]
            and e.get("financial_event_id") not in internal_transfer_ids
            and e["parsed_dt"] is not None
        ]
        salary_ids: set[str] = set()

        # Tier 2: load salary_source registry from Supabase (graceful empty on first run)
        salary_source_registry = cls._load_salary_source_registry()

        # Build sender→[events] map for Tier 3 recurring pattern detection
        sender_monthly_map: dict[str, dict[str, list[dict]]] = {}

        for c in credits:
            ev_id = c.get("financial_event_id")
            message = c["message"]
            amount = c["amount_float"]
            mkey = c["month_key"]

            # ── Tier 1: Keyword match ─────────────────────────────────────────
            if any(kw in message for kw in SALARY_KEYWORDS):
                salary_ids.add(ev_id)
                SupabaseRepo.reclassify_financial_event(uuid.UUID(ev_id), "INCOME_SALARY")
                cls_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"class-salary-{ev_id}")
                SupabaseRepo.save_transaction_classification(
                    classification_id=cls_id,
                    financial_event_id=uuid.UUID(ev_id),
                    classification="INCOME_SALARY",
                    confidence=0.95,
                )
                c["credit_subtype"] = "SALARY"
                c["category"] = "INCOME_SALARY"
                logger.info(f"Salary Tier 1 (keyword): {ev_id} amount={amount:.0f}")
                continue

            # ── Tier 2: Salary source registry match ─────────────────────────
            merchant_text = (c.get("merchant") or "").lower()
            matched_source = cls._match_salary_source(
                message, merchant_text, salary_source_registry, c["parsed_dt"], amount
            )
            if matched_source:
                salary_ids.add(ev_id)
                SupabaseRepo.reclassify_financial_event(uuid.UUID(ev_id), "INCOME_SALARY")
                cls_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"class-salary-{ev_id}")
                SupabaseRepo.save_transaction_classification(
                    classification_id=cls_id,
                    financial_event_id=uuid.UUID(ev_id),
                    classification="INCOME_SALARY",
                    confidence=0.90,
                )
                c["credit_subtype"] = "SALARY"
                c["category"] = "INCOME_SALARY"
                logger.info(f"Salary Tier 2 (registry '{matched_source}'): {ev_id} amount={amount:.0f}")
                continue

            # Accumulate for Tier 3 sender pattern analysis
            sender_key = merchant_text or message[:40]
            if mkey:
                sender_monthly_map.setdefault(sender_key, {}).setdefault(mkey, []).append(c)

            # ── Tier 4: Large unmatched credit ───────────────────────────────
            if amount >= LARGE_CREDIT_THRESHOLD:
                SupabaseRepo.reclassify_financial_event(uuid.UUID(ev_id), "INCOME_UNCLASSIFIED")
                c["category"] = "INCOME_UNCLASSIFIED"
                logger.info(f"Salary Tier 4 (large unmatched): {ev_id} amount={amount:.0f}")

        # ── Tier 3: Recurring sender pattern ─────────────────────────────────
        all_months = sorted({e["month_key"] for e in credits if e["month_key"]})
        for sender_key, monthly_events in sender_monthly_map.items():
            months_present = [m for m in all_months if m in monthly_events]
            if len(all_months) >= 4:
                recent_4 = all_months[-4:]
                months_in_recent_4 = sum(1 for m in recent_4 if m in monthly_events)
            else:
                months_in_recent_4 = len(months_present)

            if months_in_recent_4 < 3:
                continue

            # Check amount variation ≤ 15%
            sample_amounts = [
                e["amount_float"]
                for month_evs in monthly_events.values()
                for e in month_evs
            ]
            if not sample_amounts:
                continue
            avg_amount = sum(sample_amounts) / len(sample_amounts)
            if avg_amount == 0:
                continue
            variation = max(abs(a - avg_amount) / avg_amount for a in sample_amounts)
            if variation > 0.15:
                continue

            # This sender is a salary candidate
            for month_evs in monthly_events.values():
                for ev in month_evs:
                    ev_id = ev.get("financial_event_id")
                    if ev_id in salary_ids:
                        continue
                    SupabaseRepo.reclassify_financial_event(uuid.UUID(ev_id), "INCOME_SALARY_CANDIDATE")
                    ev["category"] = "INCOME_SALARY_CANDIDATE"
                    logger.info(
                        f"Salary Tier 3 (recurring pattern, sender='{sender_key[:30]}'): "
                        f"{ev_id} avg_amount={avg_amount:.0f}"
                    )

        return salary_ids

    @classmethod
    def _load_salary_source_registry(cls) -> list[dict]:
        """
        Load salary_source rows from Supabase.
        Returns empty list on first run (table may not exist yet).
        """
        try:
            res = supabase.table("salary_source").select("*").eq("is_active", True).execute()
            return res.data or []
        except Exception:
            return []  # table does not exist yet — graceful empty

    @classmethod
    def _match_salary_source(
        cls,
        message: str,
        merchant_text: str,
        registry: list[dict],
        event_dt: datetime,
        amount: float,
    ) -> str | None:
        """
        Returns the matched canonical_name if the event matches a salary_source registry entry.
        Returns None if no match.
        """
        for src in registry:
            aliases: list[str] = src.get("aliases") or []
            if not any(alias.lower() in message or alias.lower() in merchant_text
                       for alias in aliases):
                continue

            # Day-of-month check
            expected_day = src.get("expected_day_of_month")
            day_tolerance = int(src.get("day_tolerance") or 3)
            if expected_day:
                day_diff = abs(event_dt.day - int(expected_day))
                if day_diff > day_tolerance:
                    continue

            # Amount tolerance check
            expected_amount = float(src.get("expected_amount") or 0.0)
            tolerance_pct = float(src.get("amount_tolerance_pct") or 0.10)
            if expected_amount > 0:
                if abs(amount - expected_amount) / expected_amount > tolerance_pct:
                    continue

            return src.get("canonical_name") or "unknown"

        return None

    # =========================================================================
    # 3. Transaction Classification
    # =========================================================================

    @classmethod
    def classify_transactions(cls, enriched: list[dict], internal_transfer_ids: set[str]) -> None:
        """
        Classifies all non-internal-transfer debit events using FinancialClassifier.
        Updates the event category in Supabase and in-memory.
        """
        classified_count = 0
        for e in enriched:
            ev_id = e.get("financial_event_id")
            if ev_id in internal_transfer_ids:
                continue
            if e["is_credit"]:
                continue
            # Skip if already classified by a prior pass
            existing_cat = e.get("category") or ""
            if existing_cat in ("INTERNAL_TRANSFER",):
                continue

            message = e["message"]
            merchant = e.get("merchant") or ""
            paid_to = merchant

            category, confidence = FinancialClassifier.classify_transaction(
                title=message,
                merchant=merchant,
                paid_to=paid_to,
                paid_from="",
            )

            SupabaseRepo.reclassify_financial_event(uuid.UUID(ev_id), category)
            e["category"] = category

            cls_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"class-{ev_id}")
            SupabaseRepo.save_transaction_classification(
                classification_id=cls_id,
                financial_event_id=uuid.UUID(ev_id),
                classification=category,
                confidence=confidence,
            )
            classified_count += 1

        logger.info(f"  ✓ Transactions classified: {classified_count}")

    # =========================================================================
    # 4. Refund Event Processing
    # =========================================================================

    @classmethod
    def process_refund_events(
        cls, enriched: list[dict], internal_transfer_ids: set[str]
    ) -> dict[str, float]:
        """
        Processes REFUND credit events.

        For each refund:
          1. Attempt to link to a prior EXPENSE event (same merchant, within 30 days).
          2. Subtract refund amount from the ORIGINAL month's category spend.
          3. If no match: subtract from current month's EXPENSE_UNCLASSIFIED.
          4. NEVER count refund as income.

        Returns dict[month_key → total_refund_amount_offset] for AggregationService.
        """
        refund_events = [
            e for e in enriched
            if e.get("credit_subtype") == "REFUND"
            and e.get("financial_event_id") not in internal_transfer_ids
        ]

        if not refund_events:
            return {}

        # Build debit event index for matching: merchant → list of debit events
        debit_index: dict[str, list[dict]] = {}
        for e in enriched:
            if not e["is_credit"] and e.get("financial_event_id") not in internal_transfer_ids:
                merchant = (e.get("merchant") or "").lower().strip()
                if merchant:
                    debit_index.setdefault(merchant, []).append(e)

        refund_offsets: dict[str, float] = {}  # month_key → offset total

        for refund in refund_events:
            ev_id = refund.get("financial_event_id")
            amount = refund["amount_float"]
            refund_dt = refund["parsed_dt"]
            refund_merchant = (refund.get("merchant") or "").lower().strip()
            refund_mkey = refund["month_key"]

            # Classify the refund event (not income, not expense)
            SupabaseRepo.reclassify_financial_event(uuid.UUID(ev_id), "REFUND_EVENT")
            refund["category"] = "REFUND_EVENT"

            # Attempt merchant-match to originating expense
            matched_expense = None
            if refund_merchant and refund_merchant in debit_index:
                candidates = debit_index[refund_merchant]
                for candidate in sorted(candidates,
                                        key=lambda x: x["parsed_dt"],
                                        reverse=True):
                    c_dt = candidate["parsed_dt"]
                    if not c_dt or not refund_dt:
                        continue
                    days_ago = (refund_dt - c_dt).days
                    if 0 <= days_ago <= REFUND_MATCH_WINDOW_DAYS:
                        matched_expense = candidate
                        break

            if matched_expense:
                # Apply offset to the original expense's month
                target_mkey = matched_expense["month_key"] or refund_mkey
                target_cat = matched_expense.get("category") or "OTHER"
                apply_amount = min(amount, matched_expense["amount_float"])

                SupabaseRepo.update_monthly_category_spend_with_refund(
                    month_key=target_mkey,
                    category_name=target_cat,
                    refund_amount=apply_amount,
                )
                refund_offsets[target_mkey] = refund_offsets.get(target_mkey, 0.0) + apply_amount
                logger.info(
                    f"  Refund LINKED: {ev_id} ₹{amount:.0f} "
                    f"→ offset {target_mkey}/{target_cat}"
                )
            else:
                # Unlinked refund: offset current month OTHER/UNCLASSIFIED
                target_mkey = refund_mkey or "UNKNOWN"
                SupabaseRepo.update_monthly_category_spend_with_refund(
                    month_key=target_mkey,
                    category_name="OTHER",
                    refund_amount=amount,
                )
                refund_offsets[target_mkey] = refund_offsets.get(target_mkey, 0.0) + amount
                logger.info(
                    f"  Refund UNLINKED: {ev_id} ₹{amount:.0f} "
                    f"→ offset {target_mkey}/OTHER"
                )

        logger.info(f"  ✓ Refund events processed: {len(refund_events)}")
        return refund_offsets


# =============================================================================
# AggregationService — Rollup Computation (idempotent)
# =============================================================================

class AggregationService:
    """
    Owns rollup computation for the Financial Agent pipeline.

    Reads enriched financial_event facts (produced by FinancialAggregator).
    Writes to:
      - monthly_spending_summary   (accounting_spend + lifestyle_spend + income + net_flow)
      - monthly_category_spend     (per-category totals)
      - monthly_category_trends    (MoM changes)

    Idempotent: safe to re-run on the same data.
    Input: read-only access to enriched event list + refund offsets from FinancialAggregator.
    """

    @classmethod
    def run(
        cls,
        enriched: list[dict],
        internal_transfer_ids: set[str],
        salary_event_ids: set[str],
        refund_offsets_by_month: dict[str, float],
    ) -> None:
        """
        Main rollup computation entry point.

        1. Group confirmed spending events by month.
        2. Compute Accounting Spend and Lifestyle Spend per month.
        3. Compute income totals per month.
        4. Upsert monthly_spending_summary_v2.
        5. Compute category-level spends and upsert.
        6. Compute MoM trends and upsert.
        """
        logger.info("  [AggregationService] Starting rollup computation...")

        # Separate events into spending debits, income credits, transfers
        spending_events: list[dict] = []
        income_events: list[dict] = []
        internal_events: list[dict] = []

        for e in enriched:
            ev_id = e.get("financial_event_id")
            if ev_id in internal_transfer_ids:
                internal_events.append(e)
                continue
            if e["is_credit"]:
                # Only confirmed salary counts as income
                if ev_id in salary_event_ids or e.get("category") == "INCOME_SALARY":
                    income_events.append(e)
                # Refunds and other credits are excluded from income
                continue
            # Debit spending events
            spending_events.append(e)

        # Group by month
        months: set[str] = set()
        for e in enriched:
            if e["month_key"]:
                months.add(e["month_key"])

        for mkey in sorted(months):
            cls._process_month(
                month_key=mkey,
                spending=spending_events,
                income=income_events,
                internal=internal_events,
                refund_offset=refund_offsets_by_month.get(mkey, 0.0),
            )

        # MoM trends
        cls._generate_monthly_trends(sorted(months))
        logger.info("  [AggregationService] Rollup computation complete.")

    @classmethod
    def _process_month(
        cls,
        month_key: str,
        spending: list[dict],
        income: list[dict],
        internal: list[dict],
        refund_offset: float,
    ) -> None:
        """Compute and upsert all rollup rows for a single month."""

        month_spending = [e for e in spending if e["month_key"] == month_key]
        month_income = [e for e in income if e["month_key"] == month_key]
        month_internal = [e for e in internal if e["month_key"] == month_key]

        # Accounting Spend = all debits excl. internal transfers
        accounting_spend = sum(e["amount_float"] for e in month_spending)

        # Lifestyle Spend = accounting_spend − investments − insurance − cc_payments
        non_lifestyle_spend = sum(
            e["amount_float"]
            for e in month_spending
            if e.get("category") in FinancialClassifier.NON_LIFESTYLE_CATEGORIES
        )
        lifestyle_spend = max(0.0, accounting_spend - non_lifestyle_spend)

        # Break out investment/insurance for reporting
        investments = sum(
            e["amount_float"] for e in month_spending if e.get("category") == "INVESTMENT"
        )
        insurance_premiums = sum(
            e["amount_float"] for e in month_spending if e.get("category") == "INSURANCE"
        )

        # Income
        total_income = sum(e["amount_float"] for e in month_income)

        # Net Cashflow = income − accounting_spend
        net_cash_flow = total_income - accounting_spend

        # Internal transfers total (for transparency in report)
        internal_total = sum(
            e["amount_float"] for e in month_internal if not e["is_credit"]
        )

        tx_count = len(month_spending)

        summary_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"v2-summary-{month_key}")
        SupabaseRepo.save_monthly_spending_summary_v2(
            summary_id=summary_id,
            month_key=month_key,
            accounting_spend=accounting_spend,
            lifestyle_spend=lifestyle_spend,
            total_income=total_income,
            net_cash_flow=net_cash_flow,
            internal_transfers=internal_total,
            insurance_premiums=insurance_premiums,
            investments=investments,
            refund_offsets=refund_offset,
            transaction_count=tx_count,
        )

        # Category spends
        cat_spends: dict[str, float] = {}
        cat_counts: dict[str, int] = {}
        for e in month_spending:
            cat = e.get("category") or "OTHER"
            cat_spends[cat] = cat_spends.get(cat, 0.0) + e["amount_float"]
            cat_counts[cat] = cat_counts.get(cat, 0) + 1

        for cat_name, amount in cat_spends.items():
            entry_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"v2-cat-{month_key}-{cat_name}")
            SupabaseRepo.save_monthly_category_spend(
                entry_id=entry_id,
                month_key=month_key,
                category_name=cat_name,
                amount=amount,
                transaction_count=cat_counts[cat_name],
            )

        logger.info(
            f"  [AggregationService] {month_key}: "
            f"accounting=₹{accounting_spend:.0f} lifestyle=₹{lifestyle_spend:.0f} "
            f"income=₹{total_income:.0f} net=₹{net_cash_flow:.0f} "
            f"txns={tx_count}"
        )

    @classmethod
    def _generate_monthly_trends(cls, sorted_months: list[str]) -> None:
        """Compute MoM category spend changes and persist trend records."""
        all_spends = SupabaseRepo.fetch_monthly_category_spends()

        spends_map: dict[str, dict[str, float]] = {}
        for s in all_spends:
            mkey = s.get("month_key")
            if mkey:
                spends_map.setdefault(mkey, {})[s.get("category_name", "OTHER")] = float(
                    s.get("amount") or 0.0
                )

        for i, month_key in enumerate(sorted_months):
            current_spends = spends_map.get(month_key, {})
            prev_spends = spends_map.get(sorted_months[i - 1], {}) if i > 0 else {}

            for cat_name, current_amt in current_spends.items():
                prev_amt = prev_spends.get(cat_name, 0.0)
                if prev_amt > 0:
                    change_pct = ((current_amt - prev_amt) / prev_amt) * 100.0
                else:
                    change_pct = 0.0

                trend_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"v2-trend-{month_key}-{cat_name}")
                SupabaseRepo.save_monthly_category_trend(
                    trend_id=trend_id,
                    month_key=month_key,
                    category_name=cat_name,
                    current_amount=current_amt,
                    previous_amount=prev_amt,
                    change_percentage=change_pct,
                )

        logger.info(f"  [AggregationService] Trends computed for {len(sorted_months)} months.")
