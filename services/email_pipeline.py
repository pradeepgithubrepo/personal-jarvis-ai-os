from loguru import logger

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

from skills.email.todo_extractor import (
    TodoExtractor,
)

from storage.repositories.task_repository import (
    TaskRepository,
)

from storage.repositories.signal_repository import (
    SignalRepository,
)

from skills.email.category_normalizer import (
    CategoryNormalizer,
)

class EmailPipeline:

    def __init__(self):

        self.intent_extractor = (
            EmailIntentExtractor()
        )

        self.financial_extractor = (
            FinancialExtractor()
        )

        self.shopping_extractor = (
            ShoppingExtractor()
        )

        self.todo_extractor = (
            TodoExtractor()
        )

    def run(self):

        gmail_client = (
            GmailClient()
        )

        gmail_services = (
            gmail_client
            .authenticate_all_accounts()
        )

        email_reader = (
            EmailReader()
        )

        emails = (
            email_reader
            .fetch_unread_emails(
                gmail_services,
                max_results=40,
            )
        )

        logger.success(
            f"Unread emails: "
            f"{len(emails)}"
        )

        for email in emails:

            self.process_email(
                email
            )

    def process_email(
        self,
        email,
    ):

        if (
            EmailNoiseFilter
            .is_noise(email)
        ):

            logger.info(
                f"DROP → "
                f"{email['subject']}"
            )

            return

        logger.info(
            f"KEEP → "
            f"{email['subject']}"
        )

        score_result = (
            EmailScoringEngine
            .score_email(email)
        )

        intent = (
            self.intent_extractor
            .extract_intent(email)
        )


        category = (
            CategoryNormalizer
            .normalize(
                intent.get(
                    "intent",
                    "unknown",
                ),
                intent.get(
                    "category",
                    "general",
                ),
            )
        )

        details = {}

        if (
            category
            == "finance"
        ):

            details = (
                self.financial_extractor
                .extract(email)
            )

        elif (
            category
            == "shopping"
        ):

            details = (
                self.shopping_extractor
                .extract(email)
            )

        # ----------------------
        # Signal Storage
        # ----------------------

        signal_type = (
            intent.get(
                "intent",
                "unknown",
            )
        )

        if category == "finance":

            signal_type = (
                "financial_transaction"
            )

        SignalRepository.create_signal(
            source="email",
            signal_type=signal_type,
            category=category,
            importance=score_result.get(
                "priority",
                "medium",
            ),
            summary=summary,
            raw_data=details,
        )

        # ----------------------
        # Task Creation
        # ----------------------

        todo = (
            self.todo_extractor
            .extract(email)
        )

        if (
            todo.get(
                "create_task",
                False,
            )
            and
            todo.get(
                "confidence",
                0,
            ) >= 80
        ):

            TaskRepository.create_task(
                title=todo.get(
                    "title",
                    email["subject"],
                ),
                category=todo.get(
                    "category",
                    category,
                ),
                priority=todo.get(
                    "priority",
                    "medium",
                ),
                source="email",
                due_date=todo.get(
                    "due_date",
                ),
            )

        logger.success(
            f"""
Intent:
{intent.get('intent')}

Category:
{category}

Priority:
{score_result.get('priority')}

Details:
{details}
"""
        )