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
    def create_signal(
        source,
        signal_type,
        category,
        importance,
        summary,
        raw_data=None,
    ):

        session = (
            SessionLocal()
        )

        try:

            signal = Signal(
                source=source,
                signal_type=signal_type,
                category=category,
                importance=importance,
                summary=summary,
                raw_json=json.dumps(
                    raw_data
                )
                if raw_data
                else None,
            )

            session.add(
                signal
            )

            session.commit()

            logger.success(
                f"SIGNAL SAVED → "
                f"{signal_type}"
            )

        finally:

            session.close()