from loguru import logger

from services.system_initializer import (
    initialize_system,
)

from services.email_pipeline import (
    EmailPipeline,
)

from consumer.consumer_service import (
    ConsumerService,
)

from services.mobile_signal_pipeline import (
    MobileSignalPipeline,
)

from orchestration.scheduler.scheduler import (
    JarvisScheduler,
)


def startup():

    logger.info(
        "Starting Jarvis Runtime..."
    )

    initialize_system()

    # 1. Sync mobile signals from Supabase Storage
    try:
        ConsumerService().run_sync()
    except Exception as e:
        logger.error(f"Failed to sync mobile signals from Supabase at startup: {e}")

    # 2. Process unprocessed mobile signals using local LLM
    try:
        MobileSignalPipeline().run()
    except Exception as e:
        logger.error(f"Failed to process mobile signals at startup: {e}")

    # 3. Process unread emails
    try:
        EmailPipeline().run()
    except Exception as e:
        logger.error(f"Failed to process emails at startup: {e}")

    scheduler = (
        JarvisScheduler()
    )

    scheduler.start()

    logger.success(
        "Scheduler started"
    )

    return scheduler