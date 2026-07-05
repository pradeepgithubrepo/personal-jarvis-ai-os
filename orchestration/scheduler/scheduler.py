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
            self.run_morning_brief_job,
            "cron",
            hour=6,
            minute=0,
            id="morning_brief_job",
            replace_existing=True,
        )

        self.scheduler.add_job(
            self.run_evening_brief_job,
            "cron",
            hour=20,
            minute=0,
            id="evening_brief_job",
            replace_existing=True,
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
        from storage.repositories.scheduler_heartbeat_repository import scheduler_heartbeat_context
        with scheduler_heartbeat_context("runtime_heartbeat"):
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

    @staticmethod
    def run_morning_brief_job():
        from storage.db.database import SessionLocal
        from src.agents.daily_brief.agent import DailyBriefAgent
        logger.info("Executing scheduled Morning Brief job...")
        with SessionLocal() as db_session:
            try:
                DailyBriefAgent.generate_morning_brief(db_session)
                logger.success("Scheduled Morning Brief completed.")
            except Exception as e:
                logger.error(f"Failed to generate scheduled Morning Brief: {e}")

    @staticmethod
    def run_evening_brief_job():
        from storage.db.database import SessionLocal
        from src.agents.daily_brief.agent import DailyBriefAgent
        logger.info("Executing scheduled Evening Brief job...")
        with SessionLocal() as db_session:
            try:
                DailyBriefAgent.generate_evening_brief(db_session)
                logger.success("Scheduled Evening Brief completed.")
            except Exception as e:
                logger.error(f"Failed to generate scheduled Evening Brief: {e}")