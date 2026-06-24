from datetime import datetime
import json

from loguru import logger

from storage.db.database import (
    SessionLocal,
)

from storage.models.signal import (
    Signal,
)


class SignalRepository:

    @staticmethod
    def exists_message_id(message_id: str) -> bool:
        if not message_id:
            return False
        session = SessionLocal()
        try:
            return session.query(Signal).filter(Signal.message_id == message_id).first() is not None
        finally:
            session.close()

    @staticmethod
    def is_duplicate_signal(category: str, signal_type: str, details: dict, summary: str) -> bool:
        if not details:
            details = {}
        
        session = SessionLocal()
        try:
            import datetime
            import json
            # Query recent signals in last 48 hours
            limit_time = datetime.datetime.utcnow() - datetime.timedelta(days=2)
            recent_signals = session.query(Signal).filter(Signal.created_at >= limit_time).all()
            
            for sig in recent_signals:
                if not sig.raw_json:
                    continue
                try:
                    sig_details = json.loads(sig.raw_json) or {}
                except Exception:
                    continue
                
                # 1. Finance cross-channel comparison
                if category == "finance" and sig.category == "finance":
                    tx_id1 = details.get("transaction_id")
                    tx_id2 = sig_details.get("transaction_id")
                    if tx_id1 and tx_id2 and str(tx_id1).strip() == str(tx_id2).strip():
                        return True
                        
                    amt1 = details.get("amount")
                    amt2 = sig_details.get("amount")
                    if amt1 and amt2:
                        def norm_amt(a):
                            try:
                                return float(str(a).replace(",", "").replace("inr", "").replace("rs.", "").strip())
                            except Exception:
                                return str(a).strip()
                        if norm_amt(amt1) == norm_amt(amt2):
                            card1 = details.get("paid_from")
                            card2 = sig_details.get("paid_from")
                            if card1 and card2 and str(card1).strip() == str(card2).strip():
                                return True
                                
                # 2. Shopping cross-channel comparison
                elif category == "shopping" and sig.category == "shopping":
                    order_id1 = details.get("order_id") or details.get("merchant")
                    order_id2 = sig_details.get("order_id") or sig_details.get("merchant")
                    if order_id1 and order_id2 and str(order_id1).strip() == str(order_id2).strip():
                        return True
                        
                # 3. Exact matching summaries
                if summary and sig.summary:
                    if summary.strip().lower() == sig.summary.strip().lower():
                        return True
                        
            return False
        finally:
            session.close()

    @staticmethod
    def create_signal(
        source,
        signal_type,
        category,
        importance,
        summary,
        raw_data=None,
        message_id=None,
        created_at=None,
    ):

        session = SessionLocal()

        try:

            signal = Signal(
                source=source,
                signal_type=signal_type,
                category=category,
                importance=importance,
                summary=summary,
                message_id=message_id,
                raw_json=(
                    json.dumps(raw_data)
                    if raw_data
                    else None
                ),
                created_at=created_at or datetime.utcnow()
            )

            session.add(signal)

            session.commit()

            logger.success(
                f"SIGNAL SAVED → "
                f"{signal_type}"
            )

        finally:

            session.close()

    @staticmethod
    def get_today_signals():

        session = SessionLocal()

        try:

            return (
                session.query(
                    Signal
                )
                .order_by(
                    Signal.created_at.desc()
                )
                .all()
            )

        finally:

            session.close()

    @staticmethod
    def get_finance_signals():

        session = SessionLocal()

        try:

            return (
                session.query(
                    Signal
                )
                .filter(
                    Signal.category
                    == "finance"
                )
                .all()
            )

        finally:

            session.close()

    @staticmethod
    def get_shopping_signals():

        session = SessionLocal()

        try:

            return (
                session.query(
                    Signal
                )
                .filter(
                    Signal.category
                    == "shopping"
                )
                .all()
            )

        finally:

            session.close()

    @staticmethod
    def get_signals_by_category(
        category,
    ):

        session = SessionLocal()

        try:

            return (
                session.query(
                    Signal
                )
                .filter(
                    Signal.category
                    == category
                )
                .all()
            )

        finally:

            session.close()