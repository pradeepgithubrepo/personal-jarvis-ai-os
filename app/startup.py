from loguru import logger

from configs.settings import settings
from storage.db.database import initialize_database
from storage.repositories.runtime_event_repository import (
    RuntimeEventRepository,
)

from orchestration.scheduler.scheduler import (
    JarvisScheduler,
)

def startup():
    logger.info("Initializing Jarvis Runtime...")

    logger.info(f"App Name: {settings.app_name}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Local Model: {settings.local_model}")

    logger.success(
        "Configuration loaded successfully"
    )

    initialize_database()

    RuntimeEventRepository.create_event(
        event_type="startup",
        source="system",
        payload="Jarvis runtime initialized",
    )

    from intelligence.routing.router import (
    IntelligenceRouter,
    )
    from configs.constants import TaskType

    router = IntelligenceRouter()

    response = router.ask(
        prompt="Reply with READY only",
        task_type=TaskType.ROUTING,
    )

    logger.info(
        f"Router response: {response}"
    )


    scheduler = JarvisScheduler()
    scheduler.start()

    return scheduler