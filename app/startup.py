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

    # Spawn background thread for delayed pipeline run and automatic shutdown
    import threading
    from services.pipeline_orchestrator import run_delayed_pipeline_and_shutdown

    delayed_thread = threading.Thread(
        target=run_delayed_pipeline_and_shutdown,
        daemon=True,
        name="delayed_pipeline_worker"
    )
    delayed_thread.start()
    logger.success("Delayed pipeline worker thread launched successfully.")

    scheduler = (
        JarvisScheduler()
    )

    scheduler.start()

    logger.success(
        "Scheduler started"
    )

    return scheduler