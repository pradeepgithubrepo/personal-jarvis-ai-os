from loguru import logger
from apscheduler.schedulers.background import (
    BackgroundScheduler,
)


class JarvisScheduler:

    def __init__(self):
        self.scheduler = (
            BackgroundScheduler()
        )

    def start(self):
        logger.info(
            "Starting scheduler..."
        )

        self.scheduler.add_job(
            self.runtime_heartbeat,
            "interval",
            seconds=30,
            id="runtime_heartbeat",
        )

        self.scheduler.start()

        logger.success(
            "Scheduler started"
        )

    def stop(self):
        logger.info(
            "Stopping scheduler..."
        )

        self.scheduler.shutdown()

        logger.success(
            "Scheduler stopped"
        )

    @staticmethod
    def runtime_heartbeat():
        logger.info(
            "Jarvis Runtime Active..."
        )