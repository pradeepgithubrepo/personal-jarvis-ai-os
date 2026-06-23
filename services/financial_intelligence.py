# services/financial_intelligence.py

import uuid
from datetime import datetime, timedelta
from loguru import logger
from sqlalchemy import select, and_
from storage.db.database import SessionLocal
from storage.models.financial_event import FinancialEvent
from storage.models.financial_transaction_classification import FinancialTransactionClassification
from storage.models.monthly_spending_summary import MonthlySpendingSummary
from storage.models.monthly_category_spend import MonthlyCategorySpend
from storage.models.monthly_category_trend import MonthlyCategoryTrend
from services.financial_classifier import FinancialClassifier


class FinancialIntelligenceService:

    @classmethod
    def run_pipeline(cls) -> None:
        """
        Runs the full Financial Intelligence Outflow Pipeline:
        1. Detect and flag internal transfers.
        2. Classify remaining debit events.
        3. Aggregate credit, debit, and category-wise spending per calendar month.
        4. Calculate MoM trend analysis.
        """
        logger.info("Starting Financial Outflow Analysis Pipeline...")
        db = SessionLocal()
        try:
            cls.detect_and_classify_internal_transfers(db)
            cls.classify_debit_transactions(db)
            cls.generate_monthly_summaries_and_spend(db)
            cls.generate_monthly_trends(db)
            db.commit()
            logger.success("Financial Outflow Analysis Pipeline completed successfully.")
        except Exception as e:
            logger.error(f"Error running financial intelligence pipeline: {e}")
            db.rollback()
            raise e
        finally:
            db.close()

    @classmethod
    def detect_and_classify_internal_transfers(cls, db) -> None:
        """
        Flags transactions that represent internal movements between the user's accounts.
        """
        events = db.query(FinancialEvent).order_by(FinancialEvent.event_date.asc()).all()
        debits = [e for e in events if e.transaction_type == "debit"]
        credits = [e for e in events if e.transaction_type == "credit"]

        internal_transfer_ids = set()
        known_accounts_keywords = ["hdfc", "icici", "sbi", "axis", "kotak", "yono", "bank"]

        for d in debits:
            for c in credits:
                if c.id in internal_transfer_ids:
                    continue
                # 1. Matching amounts
                if d.amount and c.amount and abs(d.amount - c.amount) < 0.01:
                    # 2. Timestamps close (within 24 hours)
                    d_date = d.event_date or d.created_at
                    c_date = c.event_date or c.created_at
                    if d_date and c_date and abs(d_date - c_date) <= timedelta(hours=24):
                        # 3. Known user accounts match in descriptions
                        d_text = f"{(d.title or '')} {(d.paid_to or '')} {(d.paid_from or '')} {(d.payment_channel or '')}".lower()
                        c_text = f"{(c.title or '')} {(c.paid_to or '')} {(c.paid_from or '')} {(c.payment_channel or '')}".lower()
                        
                        d_has_acct = any(k in d_text for k in known_accounts_keywords)
                        c_has_acct = any(k in c_text for k in known_accounts_keywords)
                        
                        if d_has_acct and c_has_acct:
                            internal_transfer_ids.add(d.id)
                            internal_transfer_ids.add(c.id)
                            
                            # Update Category to INTERNAL_TRANSFER
                            d.category = "INTERNAL_TRANSFER"
                            c.category = "INTERNAL_TRANSFER"
                            db.add(d)
                            db.add(c)
                            
                            # Create Classification records
                            for ev in (d, c):
                                existing_class = db.query(FinancialTransactionClassification).filter(
                                    FinancialTransactionClassification.financial_event_id == ev.id
                                ).first()
                                if not existing_class:
                                    classification = FinancialTransactionClassification(
                                        financial_event_id=ev.id,
                                        classification="INTERNAL_TRANSFER",
                                        confidence=1.0
                                    )
                                    db.add(classification)
                            break

        db.commit()
        logger.info(f"Detected and flagged {len(internal_transfer_ids)} internal transfer legs.")

    @classmethod
    def classify_debit_transactions(cls, db) -> None:
        """
        Classifies all debit events that aren't marked as INTERNAL_TRANSFER.
        """
        debit_events = db.query(FinancialEvent).filter(
            and_(
                FinancialEvent.transaction_type == "debit",
                FinancialEvent.category != "INTERNAL_TRANSFER"
            )
        ).all()

        for ev in debit_events:
            # Check if we already have a classification
            existing = db.query(FinancialTransactionClassification).filter(
                FinancialTransactionClassification.financial_event_id == ev.id
            ).first()

            if not existing:
                category, confidence = FinancialClassifier.classify_transaction(
                    title=ev.title,
                    merchant=ev.paid_to,
                    vpa=ev.paid_to if ev.paid_to and "@" in ev.paid_to else None,
                    paid_to=ev.paid_to,
                    paid_from=ev.paid_from
                )
                
                # Update event category
                ev.category = category
                db.add(ev)

                classification = FinancialTransactionClassification(
                    financial_event_id=ev.id,
                    classification=category,
                    confidence=confidence
                )
                db.add(classification)

        db.commit()
        logger.info("Successfully classified all new debit transactions.")

    @classmethod
    def generate_monthly_summaries_and_spend(cls, db) -> None:
        """
        Aggregates outflows by calendar month.
        """
        # Fetch all debit events excluding internal transfers
        events = db.query(FinancialEvent).filter(
            and_(
                FinancialEvent.transaction_type == "debit",
                FinancialEvent.category != "INTERNAL_TRANSFER"
            )
        ).all()

        # Clear existing summaries to rebuild cleanly
        db.query(MonthlySpendingSummary).delete()
        db.query(MonthlyCategorySpend).delete()
        db.commit()

        # Group by month key YYYY-MM
        monthly_groups = {}
        for ev in events:
            date_val = ev.event_date or ev.created_at
            if not date_val:
                continue
            month_key = date_val.strftime("%Y-%m")
            if month_key not in monthly_groups:
                monthly_groups[month_key] = []
            monthly_groups[month_key].append(ev)

        for month_key, month_events in monthly_groups.items():
            total_spend = sum(e.amount or 0.0 for e in month_events)
            tx_count = len(month_events)

            summary = MonthlySpendingSummary(
                month_key=month_key,
                total_spend=total_spend,
                transaction_count=tx_count
            )
            db.add(summary)

            # Aggregate category spending
            cat_spends = {}
            cat_counts = {}
            for e in month_events:
                cat = e.category or "OTHER"
                cat_spends[cat] = cat_spends.get(cat, 0.0) + (e.amount or 0.0)
                cat_counts[cat] = cat_counts.get(cat, 0) + 1

            for cat_name, amount in cat_spends.items():
                spend_entry = MonthlyCategorySpend(
                    month_key=month_key,
                    category_name=cat_name,
                    amount=amount,
                    transaction_count=cat_counts[cat_name]
                )
                db.add(spend_entry)

        db.commit()
        logger.info("Successfully aggregated monthly spending summaries.")

    @classmethod
    def generate_monthly_trends(cls, db) -> None:
        """
        Computes Month-on-Month trends.
        """
        db.query(MonthlyCategoryTrend).delete()
        db.commit()

        summaries = db.query(MonthlySpendingSummary).order_by(MonthlySpendingSummary.month_key.asc()).all()

        for summary in summaries:
            current_month = summary.month_key
            
            # Find previous month key
            try:
                dt = datetime.strptime(current_month, "%Y-%m")
                # Subtract ~15 days to get into previous month
                prev_dt = dt - timedelta(days=15)
                prev_month = prev_dt.strftime("%Y-%m")
            except Exception:
                prev_month = None

            current_spends = db.query(MonthlyCategorySpend).filter(
                MonthlyCategorySpend.month_key == current_month
            ).all()

            previous_spends_map = {}
            if prev_month:
                prev_spends = db.query(MonthlyCategorySpend).filter(
                    MonthlyCategorySpend.month_key == prev_month
                ).all()
                for ps in prev_spends:
                    previous_spends_map[ps.category_name] = ps.amount

            for cs in current_spends:
                prev_amt = previous_spends_map.get(cs.category_name, 0.0)
                if prev_amt > 0:
                    change_pct = ((cs.amount - prev_amt) / prev_amt) * 100.0
                else:
                    change_pct = 0.0

                trend = MonthlyCategoryTrend(
                    month_key=current_month,
                    category_name=cs.category_name,
                    current_amount=cs.amount,
                    previous_amount=prev_amt,
                    change_percentage=change_pct
                )
                db.add(trend)

        db.commit()
        logger.info("Successfully generated category spending trends.")
