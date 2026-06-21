from loguru import logger
from apscheduler.schedulers.background import (
    BackgroundScheduler,
)
from configs.settings import settings
from consumer.consumer_service import ConsumerService


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

        self.scheduler.add_job(
            self.run_consumer_sync,
            "interval",
            minutes=settings.consumer_poll_interval_minutes,
            id="consumer_sync",
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

    @staticmethod
    def run_consumer_sync():
        try:
            logger.info("Triggering scheduled consumer sync...")
            ConsumerService().run_sync()
        except Exception as e:
            logger.error(f"Error in consumer sync job: {e}")