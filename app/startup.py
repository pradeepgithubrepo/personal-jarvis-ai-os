from loguru import logger

from configs.settings import settings

from storage.db.database import (
    initialize_database,
)

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

from skills.email.email_noise_filter import (
    EmailNoiseFilter,
)

from skills.email.email_scoring_engine import (
    EmailScoringEngine,
)

from skills.email.email_intent_extractor import (
    EmailIntentExtractor,
)

from skills.email.extractors.financial_extractor import (
    FinancialExtractor,
)

from skills.email.extractors.shopping_extractor import (
    ShoppingExtractor,
)


def startup():

    logger.info(
        "Initializing Jarvis Runtime..."
    )

    logger.info(
        f"App Name: "
        f"{settings.app_name}"
    )

    logger.info(
        f"Environment: "
        f"{settings.environment}"
    )

    logger.info(
        f"Local Model: "
        f"{settings.local_model}"
    )

    logger.success(
        "Configuration loaded successfully"
    )

    # ---------------------------------
    # Database Initialization
    # ---------------------------------
    initialize_database()

    RuntimeEventRepository.create_event(
        event_type="startup",
        source="system",
        payload="Jarvis runtime initialized",
    )

    # ---------------------------------
    # Intelligence Router Health Check
    # ---------------------------------
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
        f"Router response: "
        f"{response}"
    )

    # ---------------------------------
    # Gmail Authentication
    # ---------------------------------
    gmail_client = GmailClient()

    gmail_services = (
        gmail_client
        .authenticate_all_accounts()
    )

    logger.success(
        "Gmail authentication healthy"
    )

    # ---------------------------------
    # Read Emails
    # ---------------------------------
    email_reader = EmailReader()

    emails = (
        email_reader
        .fetch_unread_emails(
            gmail_services,
            max_results=40,
        )
    )

    logger.success(
        f"Total unread emails: "
        f"{len(emails)}"
    )

    # ---------------------------------
    # Initialize Intelligence Services
    # ---------------------------------
    intent_extractor = (
        EmailIntentExtractor()
    )

    financial_extractor = (
        FinancialExtractor()
    )

    shopping_extractor = (
        ShoppingExtractor()
    )

    # ---------------------------------
    # Email Signal Filtering
    # ---------------------------------
    logger.info(
        "Filtering email noise..."
    )

    filtered_emails = []

    for email in emails:

        is_noise = (
            EmailNoiseFilter
            .is_noise(email)
        )

        if is_noise:

            logger.info(
                f"DROP → "
                f"{email['subject']}"
            )

            continue

        filtered_emails.append(
            email
        )

        logger.info(
            f"KEEP → "
            f"{email['subject']} "
            f"| "
            f"{email['sender']}"
        )

        logger.info(
            f"Snippet → "
            f"{email['snippet'][:120]}"
        )

        logger.info(
            f"Body → "
            f"{email['body'][:250]}"
        )

        # ---------------------------------
        # Email Scoring
        # ---------------------------------
        score_result = (
            EmailScoringEngine
            .score_email(email)
        )

        logger.success(
            f"Priority → "
            f"{score_result['priority']} "
            f"({score_result['score']})"
        )

        # ---------------------------------
        # Intent Classification
        # ---------------------------------
        intent = (
            intent_extractor
            .extract_intent(email)
        )

        category = (
            intent.get(
                "category",
                "general",
            )
        )

        details = {}

        # ---------------------------------
        # Specialized Extractors
        # ---------------------------------
        if (
            category
            == "finance"
        ):

            details = (
                financial_extractor
                .extract(email)
            )

        elif (
            category
            == "shopping"
        ):

            details = (
                shopping_extractor
                .extract(email)
            )

        # ---------------------------------
        # Logging
        # ---------------------------------
        logger.success(
            f"""
Intent:
{intent.get(
    'intent',
    'unknown'
)}

Category:
{category}

Priority:
{intent.get(
    'priority',
    'medium'
)}

Action Required:
{intent.get(
    'action_required',
    False
)}

Details:
{details}
"""
        )

    emails = filtered_emails

    logger.success(
        f"Filtered emails: "
        f"{len(emails)}"
    )

    # ---------------------------------
    # Final Clean Output
    # ---------------------------------
    logger.info(
        "Final important emails:"
    )

    for idx, email in enumerate(
        emails,
        start=1,
    ):

        logger.success(
            f"{idx}. "
            f"{email['subject']} "
            f"| "
            f"{email['sender']}"
        )

    # ---------------------------------
    # Scheduler Start
    # ---------------------------------
    scheduler = JarvisScheduler()

    scheduler.start()

    logger.success(
        "Scheduler started"
    )

    return scheduler