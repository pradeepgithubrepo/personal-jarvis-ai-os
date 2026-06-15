from loguru import logger

from storage.db.database import SessionLocal
from storage.models.runtime_event import RuntimeEvent


class RuntimeEventRepository:

    @staticmethod
    def create_event(
        event_type: str,
        source: str,
        payload: str,
        status: str = "success",
    ):
        db = SessionLocal()

        try:
            event = RuntimeEvent(
                event_type=event_type,
                source=source,
                payload=payload,
                status=status,
            )

            db.add(event)
            db.commit()

            logger.info(
                f"Runtime event stored: {event_type}"
            )

        except Exception as ex:
            logger.error(
                f"Failed to create runtime event: {ex}"
            )
            db.rollback()

        finally:
            db.close()