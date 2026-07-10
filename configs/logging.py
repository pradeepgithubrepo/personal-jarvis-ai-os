from pathlib import Path

from loguru import logger


def setup_logging():
    log_path = Path("logs")

    log_path.mkdir(exist_ok=True)

    logger.remove()

    logger.add(
        "logs/jarvis.log",
        rotation="10 MB",
        retention="10 days",
        level="INFO",
    )

    logger.add(
        sink=lambda msg: print(msg, end=""),
        level="INFO",
    )

    logger.info("Logging initialized")

    return logger