from storage.db.database import (
    SessionLocal
)

from storage.models.mobile_signal import (
    MobileSignal
)


class MobileSignalRepository:

    @staticmethod
    def exists_hash(message_hash: str) -> bool:
        if not message_hash:
            return False
        db = SessionLocal()
        try:
            return db.query(MobileSignal).filter(MobileSignal.message_hash == message_hash).first() is not None
        finally:
            db.close()

    @staticmethod
    def save_signal(
        device_id,
        source,
        sender,
        message,
        timestamp,
        message_hash=None
    ):

        db = SessionLocal()

        try:

            signal = MobileSignal(

                device_id=device_id,

                source=source,

                sender=sender,

                message=message,

                mobile_timestamp=
                    str(timestamp),

                message_hash=message_hash
            )

            db.add(signal)

            db.commit()

        finally:

            db.close()

    @staticmethod
    def get_unprocessed_signals(limit=100):
        db = SessionLocal()
        try:
            return db.query(MobileSignal).filter(MobileSignal.processed == False).limit(limit).all()
        finally:
            db.close()

    @staticmethod
    def mark_signals_processed(signal_ids: list[int]):
        if not signal_ids:
            return
        db = SessionLocal()
        try:
            db.query(MobileSignal).filter(MobileSignal.id.in_(signal_ids)).update(
                {MobileSignal.processed: True},
                synchronize_session=False
            )
            db.commit()
        finally:
            db.close()