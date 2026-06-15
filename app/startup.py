from loguru import logger

from configs.settings import settings
from storage.db.database import initialize_database
from storage.repositories.runtime_event_repository import (
    RuntimeEventRepository,
)
from orchestration.scheduler.scheduler import (
    JarvisScheduler,
)
from ingestion.email.gmail_client import (
    GmailClient,
)

from ingestion.email.email_reader import (
    EmailReader,
)

from skills.email.email_classifier import (
    EmailClassifier,
)

def startup():
    logger.info("Initializing Jarvis Runtime...")

    logger.info(
        f"App Name: {settings.app_name}"
    )
    logger.info(
        f"Environment: {settings.environment}"
    )
    logger.info(
        f"Local Model: {settings.local_model}"
    )

    logger.success(
        "Configuration loaded successfully"
    )

    # -----------------------------
    # Database Initialization
    # -----------------------------
    initialize_database()

    RuntimeEventRepository.create_event(
        event_type="startup",
        source="system",
        payload="Jarvis runtime initialized",
    )

    # -----------------------------
    # Intelligence Router Health
    # -----------------------------
    from intelligence.routing.router import (
        IntelligenceRouter,
    )
    from configs.constants import (
        TaskType,
    )

    router = IntelligenceRouter()

    response = router.ask(
        prompt="Reply with READY only",
        task_type=TaskType.ROUTING,
    )

    logger.info(
        f"Router response: {response}"
    )

    # -----------------------------
    # Gmail Authentication
    # -----------------------------
    gmail_client = GmailClient()

    gmail_services = (
    gmail_client
    .authenticate_all_accounts()
    )

    email_reader = EmailReader()

    emails = (
        email_reader
        .fetch_unread_emails(
            gmail_services,
            max_results=20,
        )
    )

    logger.success(
        f"Total unread emails: "
        f"{len(emails)}"
    )

    for idx, email in enumerate(
        emails,
        start=1,
    ):
        logger.info(
            f"{idx}. "
            f"{email['subject']} "
            f"| {email['sender']}"
        )

    # # -----------------------------
    # # Email Classification
    # # -----------------------------
    # classifier = EmailClassifier()

    # logger.info(
    #     "Running email intelligence..."
    # )

    # for email in emails:

    #     classification = (
    #         classifier
    #         .classify_email(email)
    #     )

    #     logger.success(
    #         f"""
    # Subject:
    # {email['subject']}

    # Category:
    # {classification['category']}

    # Priority:
    # {classification['priority']}
    # """
    #     )

    # -----------------------------
    # Scheduler Start
    # -----------------------------
    scheduler = JarvisScheduler()
    scheduler.start()

    return scheduler