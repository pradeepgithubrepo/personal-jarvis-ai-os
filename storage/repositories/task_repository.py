from datetime import datetime
from loguru import logger

from storage.db.database import (
    SessionLocal,
)

from storage.models.task import (
    Task,
)


class TaskRepository:

    @staticmethod
    def create_task(
        title,
        category,
        priority,
        source,
        due_date=None,
        created_at=None,
    ):

        session = (
            SessionLocal()
        )

        try:

            task = Task(
                title=title,
                category=category,
                priority=priority,
                source=source,
                due_date=due_date,
                created_at=created_at or datetime.utcnow(),
            )

            session.add(task)

            session.commit()

            logger.success(
                f"Task created: "
                f"{title}"
            )

        finally:

            session.close()