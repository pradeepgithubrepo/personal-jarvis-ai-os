# services/financial_agent.py
"""
Financial Agent — Module 4

Entry point for all FINANCIAL class signals from the Signal Understanding Agent.

Responsibilities:
  1. Persist raw financial event (idempotent)
  2. Resolve merchant canonical name from registry
  3. Run 4-condition internal transfer detection
  4. Detect salary via 4-tier algorithm
  5. Classify expense category
  6. Write typed FinancialFact record with full lineage
  7. Update MerchantProfile
  8. Trigger AggregationService

Boundary (from Module 3 lock decision AD-3.3):
  - Does NOT reclassify SUA contracts
  - Does NOT write to qualified_signals or understood_signals tables
  - Does NOT perform any logic on non-FINANCIAL class signals
"""

import json
import re
import uuid
from datetime import datetime, timedelta, date
from loguru import logger
from sqlalchemy.orm import Session

from storage.db.database import SessionLocal
from storage.models.financial_event import FinancialEvent
from storage.models.financial_fact import FinancialFact
from storage.models.bank_account import BankAccount
from storage.models.transfer_pair import TransferPair
from storage.models.salary_source import SalarySource
from storage.models.salary_event import SalaryEvent
from storage.models.merchant import Merchant
from storage.models.merchant_profile import MerchantProfile


# ---------------------------------------------------------------------------
# Transfer type window definitions (seconds)
# ---------------------------------------------------------------------------
TRANSFER_WINDOWS = {
    "UPI":    10 * 60,
    "IMPS":   30 * 60,
    "RTGS":   2 * 3600,
    "NEFT":   4 * 3600,
    "YONO":   48 * 3600,
    "UNKNOWN": 48 * 3600,
}

# Keywords that must appear in EITHER message leg to confirm a transfer indicator
TRANSFER_INDICATOR_KWS = [
    "imps", "neft", "rtgs", "upi transfer", "fund transfer",
    "transfer to", "transfer from", "moved to", "a/c credited",
    "yono", "net banking transfer", "online transfer", "money transfer",
]

# Categories excluded from lifestyle_spend (tracked separately)
LIFESTYLE_EXCLUDED_CATEGORIES = {
    "INVESTMENT_EVENT",
    "INSURANCE_PAYMENT",
    "BILL_PAYMENT_CC",   # credit card payment (underlying spend already counted)
}

# Salary detection keywords (Tier 1)
SALARY_KEYWORDS = [
    "salary", "sal cr", "sal credit", "monthly salary",
    "basic pay", "net pay", "payroll", "sal/cr", "salary credit",
]


class FinancialAgent:
    """
    Processes a single FINANCIAL class SUA contract and writes the resulting fact.
    All methods are instance methods so the DB session can be injected for testing.
    """

    def __init__(self, db: Session | None = None):
        self._owns_session = db is None
        self.db = db or SessionLocal()
        self._bank_accounts: list[BankAccount] | None = None  # cached per instance

    def __enter__(self):
        return self

    def __exit__(self, *_):
        if self._owns_session:
            self.db.close()

    # ────────────────────────────────────────────────────────────────────────
    # Public API
    # ────────────────────────────────────────────────────────────────────────

    def process_contract(self, contract: dict) -> FinancialFact | None:
        """
        Main entry point. Accepts a canonical SUA contract dict and returns
        the created FinancialFact, or None if the signal was not FINANCIAL class.
        """
        if not isinstance(contract, dict):
            logger.warning("FinancialAgent skipped invalid non-dict contract")
            return None

        if "FINANCIAL" not in contract.get("classes", []):
            return None

        signal_id = contract.get("signal_id")
        if signal_id is None:
            logger.warning("FinancialAgent skipped contract without signal_id")
            return None

        logger.info(f"FinancialAgent processing signal {signal_id}")

        # 1. Persist / retrieve financial_event
        fin_event = self._get_or_create_financial_event(contract)
        if fin_event is None:
            logger.warning(f"Could not create financial_event for signal {signal_id}")
            return None

        existing_fact = self.db.query(FinancialFact).filter(
            FinancialFact.financial_event_id == fin_event.id
        ).first()
        if existing_fact:
            return existing_fact

        # 2. Resolve merchant
        merchant_raw, merchant_canonical, merchant_obj = self._resolve_merchant(contract)

        # 3. Determine fact type
        fact_type, transfer_pair_id, salary_source_id, salary_event = \
            self._determine_fact_type(contract, fin_event)

        # 4. Expense category
        category, confidence, method = self._classify_expense(
            contract, fact_type, merchant_canonical, merchant_obj
        )

        # 5. Aggregation control flags
        excl_accounting = fact_type == "INTERNAL_TRANSFER"
        excl_lifestyle = (
            excl_accounting
            or category in LIFESTYLE_EXCLUDED_CATEGORIES
            or fact_type in ("INSURANCE_PAYMENT", "INVESTMENT_EVENT", "BILL_PAYMENT_CC")
        )

        # 6. Event date / month
        event_date = fin_event.event_date.date() if fin_event.event_date else None
        month = date(event_date.year, event_date.month, 1) if event_date else None

        # 7. Write FinancialFact
        fact = FinancialFact(
            fact_type=fact_type,
            financial_event_id=fin_event.id,
            understood_signal_id=contract.get("signal_id"),
            amount=fin_event.amount or 0.0,
            currency=fin_event.currency or "INR",
            merchant_raw=merchant_raw,
            merchant_canonical=merchant_canonical,
            merchant_id=merchant_obj.id if merchant_obj else None,
            category=category,
            classification_confidence=confidence,
            classification_method=method,
            event_date=event_date,
            month=month,
            is_excluded_from_accounting_spend=excl_accounting,
            is_excluded_from_lifestyle_spend=excl_lifestyle,
            exclusion_reason="INTERNAL_TRANSFER" if excl_accounting else None,
            salary_source_id=salary_source_id,
            transfer_pair_id=transfer_pair_id,
        )
        self.db.add(fact)

        # 8. Update merchant profile
        if merchant_obj and event_date:
            self._update_merchant_profile(merchant_obj, fin_event.amount or 0.0, event_date)

        self.db.commit()
        logger.success(
            f"FinancialFact created — type={fact_type} category={category} "
            f"amount={fin_event.amount} signal={signal_id}"
        )
        return fact

    # ────────────────────────────────────────────────────────────────────────
    # Step 1 — Persist financial_event
    # ────────────────────────────────────────────────────────────────────────

    def _get_or_create_financial_event(self, contract: dict) -> FinancialEvent | None:
        """
        Idempotent: returns existing FinancialEvent if one already exists
        for this signal_id, otherwise creates a new one.
        """
        signal_id_str = str(contract.get("signal_id", ""))
        existing = self.db.query(FinancialEvent).filter(
            FinancialEvent.source_signal_id == signal_id_str
        ).first()
        if existing:
            return existing

        entities = self._entities(contract)
        amount = self._extract_amount(contract)
        if amount is None:
            logger.warning(
                f"Skipping financial contract {signal_id_str}: missing monetary amount"
            )
            return None

        monetary_value = entities.get("monetary_value") or {}
        currency = monetary_value.get("currency") or "INR"
        classes = contract.get("classes", [])

        # Determine transaction type from SUA contract classes
        txn_type = "debit"
        if "FINANCIAL" in classes:
            raw_context = contract.get("raw_context", {})
            sender = raw_context.get("sender", "")
            summary = (contract.get("summary") or "").lower()
            if any(kw in summary for kw in ["received", "credited to", "credit of", "refund"]):
                txn_type = "credit"

        merchants = entities.get("merchants", [])
        merchant_raw = merchants[0] if merchants else None
        orgs = entities.get("organizations", [])

        raw_ts = contract.get("raw_context", {}).get("timestamp")
        try:
            event_dt = datetime.fromisoformat(raw_ts) if raw_ts else datetime.utcnow()
        except ValueError:
            event_dt = datetime.utcnow()

        fin_event = FinancialEvent(
            title=contract.get("summary") or "Unknown transaction",
            amount=amount,
            currency=currency,
            transaction_type=txn_type,
            paid_to=merchant_raw,
            paid_from=orgs[0] if orgs else None,
            event_date=event_dt,
            source_signal_id=signal_id_str,
        )
        self.db.add(fin_event)
        self.db.flush()  # get .id without committing
        return fin_event

    def _entities(self, contract: dict) -> dict:
        entities = contract.get("entities") or {}
        return entities if isinstance(entities, dict) else {}

    def _extract_amount(self, contract: dict) -> float | None:
        entities = self._entities(contract)
        monetary_value = entities.get("monetary_value")
        if isinstance(monetary_value, dict):
            amount = monetary_value.get("amount")
            if amount is not None:
                try:
                    return float(amount)
                except (TypeError, ValueError):
                    pass

        bills = entities.get("bills")
        if isinstance(bills, dict):
            amount = bills.get("amount")
            if amount is not None:
                try:
                    return float(amount)
                except (TypeError, ValueError):
                    pass

        text = f"{contract.get('summary') or ''} {contract.get('reason') or ''}"
        match = re.search(r"(?:rs\.?|inr)\s?([\d,]+(?:\.\d+)?)", text.lower())
        if match:
            return float(match.group(1).replace(",", ""))
        return None

    # ────────────────────────────────────────────────────────────────────────
    # Step 2 — Merchant resolution
    # ────────────────────────────────────────────────────────────────────────

    def _resolve_merchant(self, contract: dict) -> tuple[str | None, str | None, Merchant | None]:
        """
        Resolves raw merchant string from SUA contract to a canonical Merchant row.
        Returns (merchant_raw, merchant_canonical, merchant_obj).

        Resolution order:
          1. Exact alias match (case-insensitive)
          2. Normalised substring match
          3. No match — returns raw string as canonical
        """
        entities = self._entities(contract)
        merchants = entities.get("merchants", [])
        raw = merchants[0] if merchants else None
        orgs = entities.get("organizations", [])
        summary = contract.get("summary") or ""
        sender = (contract.get("raw_context") or {}).get("sender", "")
        search_text = " ".join(
            str(part) for part in [raw, *orgs, sender, summary] if part
        )

        normalised = re.sub(r"[^a-z0-9\s]", "", search_text.lower()).strip()
        all_merchants = self.db.query(Merchant).all()

        # Exact alias match
        for m in all_merchants:
            for alias in (m.aliases or []):
                alias_norm = re.sub(r"[^a-z0-9\s]", "", alias.lower()).strip()
                if alias_norm and alias_norm == normalised:
                    return raw or alias, m.canonical_name, m

        # Partial / substring match
        for m in all_merchants:
            for alias in (m.aliases or []):
                alias_norm = re.sub(r"[^a-z0-9\s]", "", alias.lower()).strip()
                if alias_norm and alias_norm in normalised:
                    return raw or alias, m.canonical_name, m

        # No match — raw string is the best we have
        if raw:
            logger.debug(f"No merchant registry match for '{raw}' — using raw as canonical")
            return raw, raw, None
        return None, "UNKNOWN", None

    # ────────────────────────────────────────────────────────────────────────
    # Step 3 — Fact type determination
    # ────────────────────────────────────────────────────────────────────────

    def _determine_fact_type(
        self,
        contract: dict,
        fin_event: FinancialEvent,
    ) -> tuple[str, str | None, str | None, SalaryEvent | None]:
        """
        Determines the fact_type for this contract.
        Returns (fact_type, transfer_pair_id, salary_source_id, salary_event).

        Priority:
          1. INTERNAL_TRANSFER (if 4-condition match found)
          2. REFUND_EVENT (if contract classes include FINANCIAL and summary mentions refund)
          3. INCOME_SALARY (if credit and salary detected)
          4. INSURANCE_PAYMENT (if domains include INSURANCE and it's a debit)
          5. INVESTMENT_EVENT (if category resolves to investment)
          6. EXPENSE_EVENT (default for debits)
          7. INCOME_OTHER (default for credits)
        """
        summary_lower = (contract.get("summary") or "").lower()
        domains = contract.get("domains", [])
        reason_lower = (contract.get("reason") or "").lower()
        txn_type = fin_event.transaction_type

        # --- 1. Internal transfer detection (4 conditions) ---
        if txn_type == "debit":
            pair = self._detect_internal_transfer(fin_event, contract)
            if pair:
                return "INTERNAL_TRANSFER", pair.id, None, None

        # --- 2. Refund ---
        if any(kw in summary_lower for kw in ["refund", "reversal", "reversed", "credited back"]):
            return "REFUND_EVENT", None, None, None

        # --- 3. Salary (credit only) ---
        if txn_type == "credit":
            sal_result = self._detect_salary(fin_event, contract)
            if sal_result:
                salary_event, salary_source_id, fact_type = sal_result
                return fact_type, None, salary_source_id, salary_event

        # --- 4. Insurance payment (debit, INSURANCE in domains) ---
        if txn_type == "debit" and "INSURANCE" in domains:
            return "INSURANCE_PAYMENT", None, None, None

        # --- 5. Investment ---
        if txn_type == "debit" and any(kw in summary_lower for kw in [
            "sip", "mutual fund", "zerodha", "groww", "coin", "investment",
            "stock purchase", "nps", "ppf"
        ]):
            return "INVESTMENT_EVENT", None, None, None

        # --- 6. Bill payment (credit card payment) ---
        if txn_type == "debit" and any(kw in summary_lower for kw in [
            "sbi card", "hdfc card", "credit card payment", "card bill payment",
            "cc bill", "card outstanding"
        ]):
            return "BILL_PAYMENT_CC", None, None, None

        # --- Default ---
        if txn_type == "debit":
            return "EXPENSE_EVENT", None, None, None
        return "INCOME_OTHER", None, None, None

    # ────────────────────────────────────────────────────────────────────────
    # Internal transfer detection (4-condition algorithm)
    # ────────────────────────────────────────────────────────────────────────

    def _get_bank_accounts(self) -> list[BankAccount]:
        if self._bank_accounts is None:
            self._bank_accounts = self.db.query(BankAccount).filter(
                BankAccount.is_active == True
            ).all()
        return self._bank_accounts

    def _detect_internal_transfer(
        self, debit_event: FinancialEvent, contract: dict
    ) -> TransferPair | None:
        """
        Tests all 4 conditions. Returns a TransferPair if matched, None otherwise.

        Condition 1: Amount match (|debit − credit| < ₹1)
        Condition 2: Account ownership (both legs in bank_account registry)
        Condition 3: Transfer indicator keyword in either message
        Condition 4: Timestamp within type-specific window
        """
        if not debit_event.amount:
            return None

        bank_accounts = self._get_bank_accounts()
        debit_text = f"{debit_event.title or ''} {debit_event.paid_to or ''} {debit_event.paid_from or ''}".lower()

        # --- Condition 2a: debit sender must be a known account ---
        debit_is_known = any(
            alias.lower() in debit_text
            for ba in bank_accounts
            for alias in (ba.sender_aliases or [])
        )
        if not debit_is_known:
            return None

        # --- Condition 3: transfer indicator in debit message ---
        transfer_type = "UNKNOWN"
        for kw in TRANSFER_INDICATOR_KWS:
            if kw in debit_text:
                kw_upper = kw.upper().split()[0]
                if kw_upper in TRANSFER_WINDOWS:
                    transfer_type = kw_upper
                else:
                    transfer_type = "UNKNOWN"
                break

        if transfer_type == "UNKNOWN" and not any(kw in debit_text for kw in TRANSFER_INDICATOR_KWS):
            return None  # No transfer indicator on debit leg

        window_secs = TRANSFER_WINDOWS.get(transfer_type, TRANSFER_WINDOWS["UNKNOWN"])
        debit_dt = debit_event.event_date or debit_event.created_at
        if not debit_dt:
            return None

        # Search for matching credit event within the window
        window_start = debit_dt - timedelta(seconds=window_secs)
        window_end = debit_dt + timedelta(seconds=window_secs)

        candidate_credits = self.db.query(FinancialEvent).filter(
            FinancialEvent.transaction_type == "credit",
            FinancialEvent.event_date >= window_start,
            FinancialEvent.event_date <= window_end,
        ).all()

        for credit in candidate_credits:
            if credit.id == debit_event.id:
                continue

            # Condition 1: Amount match
            if not credit.amount or abs(debit_event.amount - credit.amount) >= 1.0:
                continue

            credit_text = f"{credit.title or ''} {credit.paid_to or ''} {credit.paid_from or ''}".lower()

            # Condition 2b: credit receiver must be a known account
            credit_is_known = any(
                alias.lower() in credit_text
                for ba in bank_accounts
                for alias in (ba.receiver_aliases or []) + (ba.sender_aliases or [])
            )
            if not credit_is_known:
                continue

            # All 4 conditions satisfied — create the pair
            pair = TransferPair(
                debit_event_id=debit_event.id,
                credit_event_id=credit.id,
                amount=debit_event.amount,
                currency=debit_event.currency or "INR",
                transfer_type=transfer_type,
                window_seconds=float(window_secs),
                confidence=1.0,
            )
            self.db.add(pair)
            # Mark both events
            debit_event.category = "INTERNAL_TRANSFER"
            credit.category = "INTERNAL_TRANSFER"
            self.db.flush()

            logger.info(
                f"Internal transfer detected: debit={debit_event.id} ↔ credit={credit.id} "
                f"amount={debit_event.amount} type={transfer_type}"
            )
            return pair

        return None

    # ────────────────────────────────────────────────────────────────────────
    # Salary detection (4-tier)
    # ────────────────────────────────────────────────────────────────────────

    def _detect_salary(
        self, credit_event: FinancialEvent, contract: dict
    ) -> tuple[SalaryEvent, str | None, str] | None:
        """
        4-tier salary detection. Returns (SalaryEvent, salary_source_id) or None.
        """
        summary = (contract.get("summary") or "").lower()
        credit_text = f"{credit_event.title or ''} {credit_event.paid_from or ''}".lower()
        amount = credit_event.amount or 0.0
        event_dt = credit_event.event_date or datetime.utcnow()
        event_date = event_dt.date() if isinstance(event_dt, datetime) else event_dt

        # --- Tier 1: Keyword match ---
        if any(kw in summary or kw in credit_text for kw in SALARY_KEYWORDS):
            sal_event = self._write_salary_event(
                credit_event, None, amount, event_date, "keyword", 0.95
            )
            return sal_event, None, "INCOME_SALARY"

        # --- Tier 2: Salary source registry match ---
        sources = self.db.query(SalarySource).filter(SalarySource.is_active == True).all()
        for source in sources:
            # Alias match
            alias_match = any(
                alias.lower() in credit_text for alias in (source.aliases or [])
            )
            if not alias_match:
                continue

            # Day-of-month match
            day_match = True
            if source.expected_day_of_month:
                tolerance = source.day_tolerance or 3
                day_match = abs(event_date.day - source.expected_day_of_month) <= tolerance

            # Amount match
            amount_match = True
            if source.expected_amount:
                tolerance_pct = source.amount_tolerance_pct or 0.10
                amount_match = abs(amount - source.expected_amount) / source.expected_amount <= tolerance_pct

            if alias_match and day_match and amount_match:
                # Update source registry
                source.last_seen = event_date
                source.expected_amount = amount  # update to latest salary
                history = source.detection_history or []
                history.append({
                    "month": event_date.strftime("%Y-%m"),
                    "amount": amount,
                    "day": event_date.day,
                    "confidence": 0.90,
                })
                source.detection_history = history
                self.db.flush()

                sal_event = self._write_salary_event(
                    credit_event, source.id, amount, event_date, "registry_match", 0.90
                )
                return sal_event, source.id, "INCOME_SALARY"

        # --- Tier 3: Recurring pattern (≥3 of last 4 months from same sender) ---
        # Look for similar credits in prior 4 months from same paid_from
        if credit_event.paid_from:
            month_start = date(event_date.year, event_date.month, 1)
            four_months_ago = date(
                (month_start - timedelta(days=120)).year,
                (month_start - timedelta(days=120)).month, 1
            )
            prior_credits = self.db.query(FinancialEvent).filter(
                FinancialEvent.transaction_type == "credit",
                FinancialEvent.paid_from == credit_event.paid_from,
                FinancialEvent.event_date >= datetime(four_months_ago.year, four_months_ago.month, 1),
                FinancialEvent.event_date < datetime(month_start.year, month_start.month, 1),
                FinancialEvent.id != credit_event.id,
            ).all()

            if len(prior_credits) >= 3:
                # Check amount variance ≤ 15%
                amounts = [c.amount for c in prior_credits if c.amount]
                if amounts and amount > 0:
                    avg = sum(amounts) / len(amounts)
                    if avg > 0 and abs(amount - avg) / avg <= 0.15:
                        # Candidate — create an unconfirmed salary_source for review
                        new_source = SalarySource(
                            canonical_name=credit_event.paid_from,
                            aliases=[credit_event.paid_from],
                            employment_type="salaried",
                            expected_day_of_month=event_date.day,
                            day_tolerance=3,
                            expected_amount=amount,
                            amount_tolerance_pct=0.15,
                            is_active=False,       # pending user confirmation
                            pending_review=True,
                            first_detected=event_date,
                            last_seen=event_date,
                            detection_history=[{
                                "month": event_date.strftime("%Y-%m"),
                                "amount": amount,
                                "day": event_date.day,
                                "confidence": 0.80,
                            }],
                        )
                        self.db.add(new_source)
                        self.db.flush()
                        logger.info(
                            f"New salary_source candidate created for '{credit_event.paid_from}' "
                            f"(pending user confirmation)"
                        )
                        sal_event = self._write_salary_event(
                            credit_event, new_source.id, amount, event_date, "pattern", 0.80
                        )
                        return sal_event, new_source.id, "INCOME_SALARY_CANDIDATE"

        # --- Tier 4: Large unclassified credit (≥ ₹20,000) ---
        if amount >= 20_000:
            source_name = credit_event.paid_from or credit_event.title or "Unknown income source"
            new_source = SalarySource(
                canonical_name=source_name[:200],
                aliases=[source_name],
                employment_type="salaried",
                expected_day_of_month=event_date.day,
                day_tolerance=5,
                expected_amount=amount,
                amount_tolerance_pct=0.20,
                is_active=False,
                pending_review=True,
                first_detected=event_date,
                last_seen=event_date,
                detection_history=[{
                    "month": event_date.strftime("%Y-%m"),
                    "amount": amount,
                    "day": event_date.day,
                    "confidence": 0.50,
                }],
            )
            self.db.add(new_source)
            self.db.flush()
            sal_event = self._write_salary_event(
                credit_event, new_source.id, amount, event_date, "large_credit", 0.50
            )
            logger.info(
                f"Large unclassified credit ₹{amount} — persisted as salary candidate"
            )
            return sal_event, new_source.id, "INCOME_SALARY_CANDIDATE"

        return None

    def _write_salary_event(
        self,
        credit_event: FinancialEvent,
        salary_source_id: str | None,
        amount: float,
        event_date: date,
        method: str,
        confidence: float,
    ) -> SalaryEvent:
        sal = SalaryEvent(
            financial_event_id=credit_event.id,
            salary_source_id=salary_source_id,
            detected_employer=credit_event.paid_from,
            gross_amount=amount,
            salary_month=date(event_date.year, event_date.month, 1),
            detection_method=method,
            confidence=confidence,
        )
        self.db.add(sal)
        self.db.flush()
        return sal

    # ────────────────────────────────────────────────────────────────────────
    # Step 4 — Expense classification
    # ────────────────────────────────────────────────────────────────────────

    def _classify_expense(
        self,
        contract: dict,
        fact_type: str,
        merchant_canonical: str | None,
        merchant_obj: Merchant | None,
    ) -> tuple[str, float, str]:
        """
        Returns (category, confidence, method).
        Only meaningful for EXPENSE_EVENT and INSURANCE_PAYMENT.
        All other fact types carry their fact_type as the category.
        """
        if fact_type != "EXPENSE_EVENT":
            return fact_type, 1.0, "fact_type"

        # Merchant registry lookup (highest priority)
        if merchant_obj:
            return merchant_obj.category, 0.95 if merchant_obj.is_trusted else 0.85, "merchant_registry"

        # Keyword fallback on summary + raw message
        summary = (contract.get("summary") or "").lower()
        kw_map = {
            "FOOD_DINING":      ["zomato", "swiggy", "restaurant", "cafe", "dining", "food order"],
            "GROCERIES":        ["bigbasket", "zepto", "blinkit", "dmart", "grocery", "grofers"],
            "MEDICAL":          ["apollo", "medplus", "pharmacy", "hospital", "clinic", "diagnostic"],
            "UTILITIES":        ["airtel", "jio", "tneb", "electricity", "broadband", "internet bill"],
            "TRANSPORT":        ["ola", "uber", "rapido", "metro", "fuel", "petrol", "toll"],
            "INSURANCE":        ["insurance", "lic", "premium", "coverfox", "policybazaar"],
            "ENTERTAINMENT":    ["netflix", "spotify", "prime", "hotstar", "pvr", "inox"],
            "SHOPPING":         ["amazon", "flipkart", "myntra", "meesho", "nykaa"],
            "EDUCATION":        ["school fee", "tuition", "byju", "unacademy"],
            "TRAVEL":           ["irctc", "makemytrip", "goibibo", "hotel"],
            "INVESTMENT":       ["sip", "mutual fund", "zerodha", "groww", "nps"],
        }
        for category, kws in kw_map.items():
            if any(kw in summary for kw in kws):
                return category, 0.80, "keyword"

        return "EXPENSE_UNCLASSIFIED", 0.50, "unmatched"

    # ────────────────────────────────────────────────────────────────────────
    # Step 8 — Merchant profile update
    # ────────────────────────────────────────────────────────────────────────

    def _update_merchant_profile(
        self, merchant: Merchant, amount: float, event_date: date
    ) -> None:
        profile = self.db.query(MerchantProfile).filter(
            MerchantProfile.merchant_id == merchant.id
        ).first()
        if not profile:
            profile = MerchantProfile(
                merchant_id=merchant.id,
                lifetime_spend=0.0,
                avg_transaction_value=0.0,
                total_transaction_count=0,
                visit_count_last_30d=0,
                visit_count_last_90d=0,
            )
            self.db.add(profile)

        today = date.today()
        profile.lifetime_spend = (profile.lifetime_spend or 0.0) + amount
        profile.total_transaction_count = (profile.total_transaction_count or 0) + 1
        profile.avg_transaction_value = (
            profile.lifetime_spend / profile.total_transaction_count
        )
        profile.last_transaction_date = event_date
        profile.last_transaction_amount = amount

        # Rolling counts (approximate — full accuracy needs a dated history table)
        if event_date >= today - timedelta(days=30):
            profile.visit_count_last_30d = (profile.visit_count_last_30d or 0) + 1
        if event_date >= today - timedelta(days=90):
            profile.visit_count_last_90d = (profile.visit_count_last_90d or 0) + 1

        self.db.flush()

    # ────────────────────────────────────────────────────────────────────────
    # Batch finalization — decisions that require the full event set
    # ────────────────────────────────────────────────────────────────────────

    def finalize_batch(self) -> dict:
        """
        Stabilizes pairwise financial facts after all contracts have been written.
        Keeps single-contract processing simple while making transfers/refunds
        reliable enough for production.
        """
        transfer_count = self._finalize_internal_transfers()
        refund_count = self._finalize_refunds()
        self.db.commit()
        return {
            "transfers_finalized": transfer_count,
            "refunds_finalized": refund_count,
        }

    def _all_account_aliases(self, bank_accounts: list[BankAccount]) -> list[str]:
        aliases: list[str] = []
        for account in bank_accounts:
            aliases.extend(account.sender_aliases or [])
            aliases.extend(account.receiver_aliases or [])
            if account.bank_name:
                aliases.append(account.bank_name)
            if account.account_number_masked:
                aliases.append(account.account_number_masked)
        return [alias.lower() for alias in aliases if alias]

    def _has_account_alias(self, text: str, aliases: list[str]) -> bool:
        text_lower = (text or "").lower()
        return any(alias in text_lower for alias in aliases)

    def _transfer_type_from_text(self, text: str) -> str:
        text_lower = (text or "").lower()
        for keyword in TRANSFER_INDICATOR_KWS:
            if keyword in text_lower:
                candidate = keyword.upper().split()[0]
                return candidate if candidate in TRANSFER_WINDOWS else "UNKNOWN"
        if "yono" in text_lower:
            return "YONO"
        return "UNKNOWN"

    def _finalize_internal_transfers(self) -> int:
        bank_accounts = self._get_bank_accounts()
        aliases = self._all_account_aliases(bank_accounts)
        if not aliases:
            return 0

        existing_event_ids = {
            row[0]
            for row in self.db.query(TransferPair.debit_event_id).all()
        } | {
            row[0]
            for row in self.db.query(TransferPair.credit_event_id).all()
        }

        debits = self.db.query(FinancialEvent).filter(
            FinancialEvent.transaction_type == "debit",
            FinancialEvent.amount.isnot(None),
        ).order_by(FinancialEvent.event_date.asc()).all()
        credits = self.db.query(FinancialEvent).filter(
            FinancialEvent.transaction_type == "credit",
            FinancialEvent.amount.isnot(None),
        ).order_by(FinancialEvent.event_date.asc()).all()

        facts_by_event_id = {
            fact.financial_event_id: fact
            for fact in self.db.query(FinancialFact).all()
        }

        created = 0
        used_credit_ids = set(existing_event_ids)

        for debit in debits:
            if debit.id in existing_event_ids:
                continue
            debit_dt = debit.event_date or debit.created_at
            if not debit_dt or not debit.amount:
                continue
            debit_text = f"{debit.title or ''} {debit.paid_to or ''} {debit.paid_from or ''}"
            debit_known = self._has_account_alias(debit_text, aliases)
            if not debit_known:
                continue

            best_credit = None
            best_gap = None
            best_transfer_type = "UNKNOWN"

            for credit in credits:
                if credit.id in used_credit_ids or credit.id == debit.id:
                    continue
                if not credit.amount or abs(debit.amount - credit.amount) >= 1.0:
                    continue
                credit_dt = credit.event_date or credit.created_at
                if not credit_dt:
                    continue
                combined_text = (
                    f"{debit_text} {credit.title or ''} "
                    f"{credit.paid_to or ''} {credit.paid_from or ''}"
                )
                credit_known = self._has_account_alias(combined_text, aliases)
                if not credit_known:
                    continue

                transfer_type = self._transfer_type_from_text(combined_text)
                window_seconds = TRANSFER_WINDOWS.get(
                    transfer_type,
                    TRANSFER_WINDOWS["UNKNOWN"],
                )
                gap_seconds = abs((debit_dt - credit_dt).total_seconds())
                if gap_seconds > window_seconds:
                    continue
                if best_gap is None or gap_seconds < best_gap:
                    best_credit = credit
                    best_gap = gap_seconds
                    best_transfer_type = transfer_type

            if best_credit is None:
                continue

            pair = TransferPair(
                debit_event_id=debit.id,
                credit_event_id=best_credit.id,
                amount=debit.amount,
                currency=debit.currency or best_credit.currency or "INR",
                transfer_type=best_transfer_type,
                window_seconds=float(
                    TRANSFER_WINDOWS.get(
                        best_transfer_type,
                        TRANSFER_WINDOWS["UNKNOWN"],
                    )
                ),
                confidence=1.0,
            )
            self.db.add(pair)
            self.db.flush()

            for event in (debit, best_credit):
                event.category = "INTERNAL_TRANSFER"
                fact = facts_by_event_id.get(event.id)
                if fact:
                    fact.fact_type = "INTERNAL_TRANSFER"
                    fact.category = "INTERNAL_TRANSFER"
                    fact.classification_confidence = 1.0
                    fact.classification_method = "transfer_pair"
                    fact.is_excluded_from_accounting_spend = True
                    fact.is_excluded_from_lifestyle_spend = True
                    fact.exclusion_reason = "INTERNAL_TRANSFER"
                    fact.transfer_pair_id = pair.id

            existing_event_ids.add(debit.id)
            existing_event_ids.add(best_credit.id)
            used_credit_ids.add(best_credit.id)
            created += 1

        return created

    def _finalize_refunds(self) -> int:
        refund_facts = self.db.query(FinancialFact).filter(
            FinancialFact.fact_type == "REFUND_EVENT"
        ).all()
        expense_facts = self.db.query(FinancialFact).filter(
            FinancialFact.fact_type == "EXPENSE_EVENT"
        ).all()

        linked = 0
        for refund in refund_facts:
            refund.is_excluded_from_accounting_spend = True
            refund.is_excluded_from_lifestyle_spend = True
            refund.exclusion_reason = "REFUND_OFFSET"

            if refund.refund_of_fact_id or not refund.amount or not refund.event_date:
                continue

            candidates = []
            for expense in expense_facts:
                if expense.is_refunded or not expense.amount or not expense.event_date:
                    continue
                if expense.event_date > refund.event_date:
                    continue
                if (refund.event_date - expense.event_date).days > 30:
                    continue
                if abs(expense.amount - refund.amount) >= 1.0:
                    continue
                merchant_match = (
                    refund.merchant_canonical
                    and expense.merchant_canonical
                    and refund.merchant_canonical == expense.merchant_canonical
                )
                candidates.append((0 if merchant_match else 1, expense.event_date, expense))

            if not candidates:
                refund.refund_applied_to_month = refund.month
                continue

            _, _, matched = sorted(
                candidates,
                key=lambda item: (item[0], -item[1].toordinal()),
            )[0]
            refund.refund_of_fact_id = matched.id
            refund.refund_applied_to_month = matched.month
            matched.is_refunded = True
            linked += 1

        return linked

    @classmethod
    def process_all_understood_financial_signals(cls) -> dict:
        from storage.models.understood_signal import UnderstoodSignal

        db = SessionLocal()
        processed = 0
        skipped = 0
        failed = 0
        try:
            rows = db.query(UnderstoodSignal).all()
            with cls(db=db) as agent:
                for row in rows:
                    try:
                        contract = json.loads(row.contract_json)
                    except Exception as exc:
                        logger.warning(
                            f"Skipping understood_signal {row.id}: invalid contract JSON ({exc})"
                        )
                        skipped += 1
                        continue

                    if "FINANCIAL" not in contract.get("classes", []):
                        continue

                    try:
                        fact = agent.process_contract(contract)
                        if fact is None:
                            skipped += 1
                        else:
                            processed += 1
                    except Exception as exc:
                        db.rollback()
                        failed += 1
                        logger.exception(
                            f"FinancialAgent failed for understood_signal {row.id}: {exc}"
                        )

                finalization = agent.finalize_batch()

            return {
                "processed": processed,
                "skipped": skipped,
                "failed": failed,
                **finalization,
            }
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Module-level convenience function (for pipeline orchestration)
# ---------------------------------------------------------------------------

def process_financial_contract(contract: dict) -> FinancialFact | None:
    """
    Convenience wrapper. Creates a short-lived FinancialAgent session,
    processes the contract, then triggers aggregation.
    """
    from services.aggregation_service import AggregationService

    with FinancialAgent() as agent:
        fact = agent.process_contract(contract)

    if fact and fact.month:
        month_key = fact.month.strftime("%Y-%m")
        AggregationService.run_for_month(month_key)

    return fact
