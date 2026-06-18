from loguru import logger

from services.system_initializer import (
    initialize_system,
)

from services.email_pipeline import (
    EmailPipeline,
)

from orchestration.scheduler.scheduler import (
    JarvisScheduler,
)


def startup():

    logger.info(
        "Starting Jarvis Runtime..."
    )

    initialize_system()

    EmailPipeline().run()

    scheduler = (
        JarvisScheduler()
    )

    scheduler.start()

    logger.success(
        "Scheduler started"
    )

    return scheduler