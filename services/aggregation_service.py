# services/aggregation_service.py
"""
Aggregation Service — Module 4

Owned tables:
  monthly_spending_summary
  monthly_category_spend
  monthly_merchant_spend   (via MonthlyCategorySpend with merchant_canonical column)

Boundary:
  - Reads from financial_facts (read-only access to Financial Agent tables)
  - Writes ONLY to its own rollup tables
  - Idempotent: re-running for the same month produces the same result

Split spend views (from financial_agent_v2_revision.md):
  Accounting Spend = all EXPENSE_EVENT facts (excl. INTERNAL_TRANSFER)
  Lifestyle Spend  = Accounting Spend − INVESTMENT_EVENT − INSURANCE_PAYMENT − BILL_PAYMENT_CC
"""

from datetime import date, datetime
from loguru import logger
from sqlalchemy import and_

from storage.db.database import SessionLocal
from storage.models.financial_fact import FinancialFact
from storage.models.monthly_spending_summary import MonthlySpendingSummary
from storage.models.monthly_category_spend import MonthlyCategorySpend
from storage.models.monthly_category_trend import MonthlyCategoryTrend


class AggregationService:

    # Fact types that are outflows but excluded from lifestyle spend
    LIFESTYLE_EXCLUDED_FACT_TYPES = {
        "INVESTMENT_EVENT",
        "INSURANCE_PAYMENT",
        "BILL_PAYMENT_CC",
    }

    @classmethod
    def run_for_month(cls, month_key: str) -> MonthlySpendingSummary:
        """
        Recomputes and upserts all aggregations for the given month.
        month_key format: 'YYYY-MM'

        This method is idempotent — safe to call multiple times for the same month.
        """
        logger.info(f"AggregationService: computing rollups for {month_key}")
        db = SessionLocal()
        try:
            summary = cls._aggregate_month(db, month_key)
            db.commit()
            logger.success(
                f"AggregationService: {month_key} → "
                f"accounting=₹{summary.accounting_spend:.0f} "
                f"lifestyle=₹{summary.lifestyle_spend:.0f} "
                f"income=₹{summary.total_income:.0f} "
                f"net=₹{summary.net_cash_flow:.0f}"
            )
            return summary
        except Exception as e:
            db.rollback()
            logger.error(f"AggregationService failed for {month_key}: {e}")
            raise
        finally:
            db.close()

    @classmethod
    def run_all(cls) -> None:
        """
        Re-aggregates all months present in financial_facts.
        Used on first run or after data corrections.
        """
        db = SessionLocal()
        try:
            all_months = db.query(FinancialFact.month).distinct().all()
            month_keys = sorted({
                m[0].strftime("%Y-%m") for m in all_months if m[0]
            })
            logger.info(f"AggregationService.run_all: {len(month_keys)} months to process")
            for month_key in month_keys:
                cls._aggregate_month(db, month_key)
            cls._compute_category_trends(db)
            db.commit()
            logger.success("AggregationService.run_all complete")
        except Exception as e:
            db.rollback()
            logger.error(f"AggregationService.run_all failed: {e}")
            raise
        finally:
            db.close()

    # ────────────────────────────────────────────────────────────────────────
    # Core aggregation logic
    # ────────────────────────────────────────────────────────────────────────

    @classmethod
    def _aggregate_month(cls, db, month_key: str) -> MonthlySpendingSummary:
        # Parse month into date bounds
        try:
            month_dt = datetime.strptime(month_key, "%Y-%m")
            month_date = date(month_dt.year, month_dt.month, 1)
        except ValueError:
            raise ValueError(f"Invalid month_key format: '{month_key}' — expected YYYY-MM")

        # Load all facts for this month
        facts = db.query(FinancialFact).filter(
            FinancialFact.month == month_date
        ).all()

        # ── Bucket all facts ──────────────────────────────────────────────
        accounting_spend = 0.0
        lifestyle_spend = 0.0
        total_debits = 0.0
        total_credits = 0.0
        total_income = 0.0
        internal_transfers = 0.0
        insurance_premiums = 0.0
        investments = 0.0
        refund_offsets = 0.0
        tx_count = 0

        # Category and merchant buckets for rollup tables
        category_amounts: dict[str, float] = {}
        category_counts: dict[str, int] = {}
        merchant_amounts: dict[str, float] = {}
        merchant_counts: dict[str, int] = {}

        for fact in facts:
            amount = fact.amount or 0.0

            if fact.fact_type in (
                "INCOME_SALARY",
                "INCOME_SALARY_CANDIDATE",
                "INCOME_OTHER",
                "REFUND_EVENT",
            ):
                total_credits += amount
            else:
                total_debits += amount

            # --- Refund (spending offset) ---
            if fact.fact_type == "REFUND_EVENT":
                refund_offsets += amount
                continue

            # --- Income ---
            if fact.fact_type in (
                "INCOME_SALARY",
                "INCOME_SALARY_CANDIDATE",
                "INCOME_OTHER",
            ):
                total_income += amount
                continue

            # --- Internal transfers ---
            if fact.fact_type == "INTERNAL_TRANSFER" or fact.is_excluded_from_accounting_spend:
                internal_transfers += amount
                continue

            # --- Remaining outflows ---
            # Apply refund offset to this fact if it has been refunded
            effective_amount = amount
            if fact.is_refunded:
                # The refund is tracked separately — this fact's gross is still counted
                # and the offset row reduces it; we keep gross here for transparency
                pass

            accounting_spend += effective_amount
            tx_count += 1

            # Lifestyle exclusions
            if (
                fact.fact_type in cls.LIFESTYLE_EXCLUDED_FACT_TYPES
                or fact.is_excluded_from_lifestyle_spend
            ):
                if fact.fact_type == "INSURANCE_PAYMENT":
                    insurance_premiums += effective_amount
                elif fact.fact_type == "INVESTMENT_EVENT":
                    investments += effective_amount
                # BILL_PAYMENT_CC tracked under accounting only
            else:
                lifestyle_spend += effective_amount

            # Category rollup
            category = fact.category or "EXPENSE_UNCLASSIFIED"
            category_amounts[category] = category_amounts.get(category, 0.0) + effective_amount
            category_counts[category] = category_counts.get(category, 0) + 1

            # Merchant rollup
            merchant = fact.merchant_canonical or "Unknown"
            merchant_amounts[merchant] = merchant_amounts.get(merchant, 0.0) + effective_amount
            merchant_counts[merchant] = merchant_counts.get(merchant, 0) + 1

        # Apply refund offsets to the accounting and lifestyle totals
        accounting_spend = max(0.0, accounting_spend - refund_offsets)
        lifestyle_spend = max(0.0, lifestyle_spend - refund_offsets)

        net_cash_flow = total_income - accounting_spend

        # ── Upsert MonthlySpendingSummary ──────────────────────────────────
        existing_summary = db.query(MonthlySpendingSummary).filter(
            MonthlySpendingSummary.month_key == month_key
        ).first()
        if existing_summary:
            existing_summary.total_spend = accounting_spend
            existing_summary.total_debits = total_debits
            existing_summary.total_credits = total_credits
            existing_summary.accounting_spend = accounting_spend
            existing_summary.lifestyle_spend = lifestyle_spend
            existing_summary.total_income = total_income
            existing_summary.net_cash_flow = net_cash_flow
            existing_summary.internal_transfers = internal_transfers
            existing_summary.insurance_premiums = insurance_premiums
            existing_summary.investments = investments
            existing_summary.refund_offsets = refund_offsets
            existing_summary.transaction_count = tx_count
            summary = existing_summary
        else:
            summary = MonthlySpendingSummary(
                month_key=month_key,
                total_spend=accounting_spend,
                total_debits=total_debits,
                total_credits=total_credits,
                accounting_spend=accounting_spend,
                lifestyle_spend=lifestyle_spend,
                total_income=total_income,
                net_cash_flow=net_cash_flow,
                internal_transfers=internal_transfers,
                insurance_premiums=insurance_premiums,
                investments=investments,
                refund_offsets=refund_offsets,
                transaction_count=tx_count,
            )
            db.add(summary)

        # ── Upsert MonthlyCategorySpend ────────────────────────────────────
        # Delete existing for this month and re-insert (idempotent)
        db.query(MonthlyCategorySpend).filter(
            MonthlyCategorySpend.month_key == month_key
        ).delete()

        for cat, amt in category_amounts.items():
            db.add(MonthlyCategorySpend(
                month_key=month_key,
                category_name=cat,
                amount=amt,
                transaction_count=category_counts.get(cat, 0),
            ))

        db.flush()
        return summary

    @classmethod
    def _compute_category_trends(cls, db) -> None:
        db.query(MonthlyCategoryTrend).delete()

        spends = db.query(MonthlyCategorySpend).order_by(
            MonthlyCategorySpend.month_key.asc()
        ).all()
        by_month_category = {
            (spend.month_key, spend.category_name): spend.amount
            for spend in spends
        }
        month_keys = sorted({spend.month_key for spend in spends})

        for month_key in month_keys:
            dt = datetime.strptime(month_key, "%Y-%m")
            if dt.month == 1:
                prev_key = f"{dt.year - 1}-12"
            else:
                prev_key = f"{dt.year}-{dt.month - 1:02d}"

            current_spends = [
                spend for spend in spends if spend.month_key == month_key
            ]
            for spend in current_spends:
                previous_amount = by_month_category.get(
                    (prev_key, spend.category_name),
                    0.0,
                )
                if previous_amount > 0:
                    change_percentage = (
                        (spend.amount - previous_amount) / previous_amount
                    ) * 100.0
                else:
                    change_percentage = 0.0
                db.add(MonthlyCategoryTrend(
                    month_key=month_key,
                    category_name=spend.category_name,
                    current_amount=spend.amount,
                    previous_amount=previous_amount,
                    change_percentage=change_percentage,
                ))

    # ────────────────────────────────────────────────────────────────────────
    # Convenience: month-over-month trend (read-only, no writes)
    # ────────────────────────────────────────────────────────────────────────

    @classmethod
    def get_trend(cls, month_key: str) -> dict:
        """
        Returns month-over-month trend data for the given month.
        Reads from monthly_spending_summary — no writes.
        """
        db = SessionLocal()
        try:
            from datetime import datetime
            dt = datetime.strptime(month_key, "%Y-%m")
            # Previous month
            if dt.month == 1:
                prev_key = f"{dt.year - 1}-12"
            else:
                prev_key = f"{dt.year}-{dt.month - 1:02d}"

            current = db.query(MonthlySpendingSummary).filter(
                MonthlySpendingSummary.month_key == month_key
            ).first()
            previous = db.query(MonthlySpendingSummary).filter(
                MonthlySpendingSummary.month_key == prev_key
            ).first()

            def pct_change(curr, prev):
                if prev and prev > 0:
                    return round((curr - prev) / prev * 100, 1)
                return None

            return {
                "month": month_key,
                "accounting_spend": current.accounting_spend if current else 0,
                "lifestyle_spend": current.lifestyle_spend if current else 0,
                "total_income": current.total_income if current else 0,
                "net_cash_flow": current.net_cash_flow if current else 0,
                "vs_previous_month": {
                    "accounting_spend_pct": pct_change(
                        current.accounting_spend if current else 0,
                        previous.accounting_spend if previous else 0,
                    ),
                    "lifestyle_spend_pct": pct_change(
                        current.lifestyle_spend if current else 0,
                        previous.lifestyle_spend if previous else 0,
                    ),
                    "income_pct": pct_change(
                        current.total_income if current else 0,
                        previous.total_income if previous else 0,
                    ),
                },
            }
        finally:
            db.close()
