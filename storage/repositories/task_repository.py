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
            )

            session.add(task)

            session.commit()

            logger.success(
                f"Task created: "
                f"{title}"
            )

        finally:

            session.close()