# services/financial_aggregator.py

import uuid
from datetime import datetime, timedelta
from loguru import logger
from services.supabase_repo import SupabaseRepo, supabase
from services.financial_classifier import FinancialClassifier


class FinancialAggregator:

    @classmethod
    def run_aggregation(cls) -> None:
        """
        Runs the full Financial Aggregation pipeline on Supabase data:
        1. Fetch all financial events and signals.
        2. Detect internal transfers and flag them.
        3. Classify all remaining debit events using FinancialClassifier.
        4. Clear existing summary tables in Supabase.
        5. Aggregate and save monthly spending summaries, category spends, and MoM trends.
        """
        logger.info("Starting Financial Aggregator pipeline...")

        events = SupabaseRepo.fetch_financial_events()
        if not events:
            logger.warning("No financial events found in Supabase. Cannot aggregate.")
            return

        # Fetch signals to resolve credit/debit transaction types and titles
        try:
            signals_data = supabase.table("signals").select("signal_id, message").execute().data or []
            signal_messages = {s["signal_id"]: s["message"] for s in signals_data}
        except Exception as e:
            logger.error(f"Failed to fetch signals from Supabase: {e}")
            signal_messages = {}

        # 1. Clear existing summary tables
        SupabaseRepo.clear_summary_tables()

        # 2. Detect and flag Internal Transfers
        internal_transfer_leg_ids = cls.detect_internal_transfers(events, signal_messages)

        # 3. Classify debit transactions and save classifications
        cls.classify_transactions(events, signal_messages, internal_transfer_leg_ids)

        # 4. Filter out internal transfers and credit events for spending rollups
        spending_events = []
        for e in events:
            e_id = e.get("financial_event_id")
            if e_id in internal_transfer_leg_ids:
                continue

            sig_id = e.get("source_signal_id")
            message = (signal_messages.get(sig_id) or "").lower()
            
            is_credit = "credited" in message or "salary" in message or "received" in message or "deposit" in message or "credit alert" in message
            if not is_credit:
                spending_events.append(e)

        # 5. Group by calendar month YYYY-MM
        monthly_groups = {}
        for e in spending_events:
            dt_str = e.get("event_timestamp")
            if not dt_str:
                continue
            try:
                dt_clean = dt_str.replace("Z", "").split(".")[0]
                dt = datetime.fromisoformat(dt_clean)
                month_key = dt.strftime("%Y-%m")
            except Exception:
                continue

            if month_key not in monthly_groups:
                monthly_groups[month_key] = []
            monthly_groups[month_key].append(e)

        # 6. Save Monthly Summaries and Category Spends
        for month_key, month_events in monthly_groups.items():
            total_spend = sum(float(e.get("amount") or 0.0) for e in month_events)
            tx_count = len(month_events)

            summary_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"financial-summary-{month_key}")
            SupabaseRepo.save_monthly_spending_summary(
                summary_id=summary_id,
                month_key=month_key,
                total_spend=total_spend,
                transaction_count=tx_count
            )

            # Aggregate category spending
            cat_spends = {}
            cat_counts = {}
            for e in month_events:
                cat = e.get("category") or "OTHER"
                cat_spends[cat] = cat_spends.get(cat, 0.0) + float(e.get("amount") or 0.0)
                cat_counts[cat] = cat_counts.get(cat, 0) + 1

            for cat_name, amt in cat_spends.items():
                entry_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"category-spend-{month_key}-{cat_name}")
                SupabaseRepo.save_monthly_category_spend(
                    entry_id=entry_id,
                    month_key=month_key,
                    category_name=cat_name,
                    amount=amt,
                    transaction_count=cat_counts[cat_name]
                )

        # 7. Generate MoM Trends
        cls.generate_monthly_trends(list(monthly_groups.keys()))

        logger.success("Financial Aggregator pipeline run complete.")

    @classmethod
    def detect_internal_transfers(cls, events: list[dict], signal_messages: dict) -> set[str]:
        """
        Detects internal transfers matching debits and credits on Supabase.
        Returns a set of transaction/event IDs that represent internal transfers.
        """
        debits = []
        credits = []
        known_accounts_keywords = ["hdfc", "icici", "sbi", "axis", "kotak", "yono", "bank"]

        for e in events:
            sig_id = e.get("source_signal_id")
            message = (signal_messages.get(sig_id) or "").lower()
            is_credit = "credited" in message or "salary" in message or "received" in message or "deposit" in message or "credit alert" in message
            
            dt_str = e.get("event_timestamp")
            if dt_str:
                try:
                    dt_clean = dt_str.replace("Z", "").split(".")[0]
                    dt = datetime.fromisoformat(dt_clean)
                    item = {"event": e, "date": dt, "amount": float(e.get("amount") or 0), "message": message}
                    if is_credit:
                        credits.append(item)
                    else:
                        debits.append(item)
                except Exception:
                    pass

        internal_transfer_ids = set()
        for d in debits:
            for c in credits:
                c_event_id = c["event"].get("financial_event_id")
                if c_event_id in internal_transfer_ids:
                    continue
                # Match Amount
                if abs(d["amount"] - c["amount"]) < 0.01:
                    # Match Timestamp (within 24 hours)
                    if abs(d["date"] - c["date"]) <= timedelta(hours=24):
                        # Match Bank Keywords
                        d_text = f"{d['message']} {d['event'].get('merchant', '')}".lower()
                        c_text = f"{c['message']} {c['event'].get('merchant', '')}".lower()
                        
                        d_has_acct = any(k in d_text for k in known_accounts_keywords)
                        c_has_acct = any(k in c_text for k in known_accounts_keywords)
                        
                        if d_has_acct and c_has_acct:
                            d_event_id = d["event"].get("financial_event_id")
                            internal_transfer_ids.add(d_event_id)
                            internal_transfer_ids.add(c_event_id)
                            
                            # Mark categories directly in Supabase
                            SupabaseRepo.reclassify_financial_event(uuid.UUID(d_event_id), "INTERNAL_TRANSFER")
                            SupabaseRepo.reclassify_financial_event(uuid.UUID(c_event_id), "INTERNAL_TRANSFER")
                            
                            # Log classification records to Supabase classification table
                            for ev_id in (d_event_id, c_event_id):
                                classification_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"class-{ev_id}")
                                SupabaseRepo.save_transaction_classification(
                                    classification_id=classification_id,
                                    financial_event_id=uuid.UUID(ev_id),
                                    classification="INTERNAL_TRANSFER",
                                    confidence=1.0
                                )
                            break
        return internal_transfer_ids

    @classmethod
    def classify_transactions(cls, events: list[dict], signal_messages: dict, internal_transfer_ids: set[str]) -> None:
        """
        Classifies all non-internal-transfer debits on Supabase.
        """
        for e in events:
            e_id = e.get("financial_event_id")
            if e_id in internal_transfer_ids:
                continue

            sig_id = e.get("source_signal_id")
            message = (signal_messages.get(sig_id) or "").lower()
            is_credit = "credited" in message or "salary" in message or "received" in message or "deposit" in message or "credit alert" in message
            
            if not is_credit:
                # Classify debit transaction
                title = message
                merchant = e.get("merchant") or ""
                paid_to = merchant
                paid_from = ""
                
                category, confidence = FinancialClassifier.classify_transaction(
                    title=title,
                    merchant=merchant,
                    paid_to=paid_to,
                    paid_from=paid_from
                )

                # Reclassify event category in Supabase
                SupabaseRepo.reclassify_financial_event(uuid.UUID(e_id), category)
                e["category"] = category

                # Save transaction classification
                classification_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"class-{e_id}")
                SupabaseRepo.save_transaction_classification(
                    classification_id=classification_id,
                    financial_event_id=uuid.UUID(e_id),
                    classification=category,
                    confidence=confidence
                )

    @classmethod
    def generate_monthly_trends(cls, month_keys: list[str]) -> None:
        """
        Generates trends and uploads MoM changes.
        """
        all_spends = SupabaseRepo.fetch_monthly_category_spends()
        
        # Group spends by month key
        spends_map = {}
        for s in all_spends:
            m_key = s.get("month_key")
            if m_key not in spends_map:
                spends_map[m_key] = []
            spends_map[m_key].append(s)

        # Sort month keys chronologically
        sorted_months = sorted(month_keys)

        for i, month_key in enumerate(sorted_months):
            current_spends = spends_map.get(month_key, [])
            
            previous_spends_map = {}
            if i > 0:
                prev_month = sorted_months[i - 1]
                prev_spends = spends_map.get(prev_month, [])
                for ps in prev_spends:
                    previous_spends_map[ps.get("category_name")] = float(ps.get("amount") or 0.0)

            for cs in current_spends:
                cat_name = cs.get("category_name")
                current_amt = float(cs.get("amount") or 0.0)
                prev_amt = previous_spends_map.get(cat_name, 0.0)

                if prev_amt > 0:
                    change_pct = ((current_amt - prev_amt) / prev_amt) * 100.0
                else:
                    change_pct = 0.0

                trend_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"category-trend-{month_key}-{cat_name}")
                SupabaseRepo.save_monthly_category_trend(
                    trend_id=trend_id,
                    month_key=month_key,
                    category_name=cat_name,
                    current_amount=current_amt,
                    previous_amount=prev_amt,
                    change_percentage=change_pct
                )
