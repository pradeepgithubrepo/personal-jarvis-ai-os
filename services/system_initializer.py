from loguru import logger

from configs.settings import (
    settings,
)

from storage.db.database import (
    initialize_database,
)

from storage.repositories.runtime_event_repository import (
    RuntimeEventRepository,
)

from intelligence.routing.router import (
    IntelligenceRouter,
)

from configs.constants import (
    TaskType,
)


def initialize_system():

    logger.info(
        f"App Name: "
        f"{settings.app_name}"
    )

    logger.info(
        f"Environment: "
        f"{settings.environment}"
    )

    logger.info(
        f"Local Model: "
        f"{settings.local_model}"
    )

    initialize_database()

    RuntimeEventRepository.create_event(
        event_type="startup",
        source="system",
        payload="Jarvis runtime initialized",
    )

    router = (
        IntelligenceRouter()
    )

    response = (
        router.ask(
            prompt="Reply with READY only",
            task_type=TaskType.ROUTING,
        )
    )

    logger.success(
        f"Router: {response}"
    )