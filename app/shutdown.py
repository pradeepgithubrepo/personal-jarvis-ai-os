from loguru import logger

from storage.repositories.runtime_event_repository import (
    RuntimeEventRepository,
)


def shutdown(scheduler=None):
    logger.info(
        "Shutting down Jarvis Runtime..."
    )

    RuntimeEventRepository.create_event(
        event_type="shutdown",
        source="system",
        payload="Jarvis runtime shutdown",
    )

    if scheduler:
        scheduler.stop()