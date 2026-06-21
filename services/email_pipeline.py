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
from skills.email.email_intent_extractor import (
    EmailIntentExtractor,
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
        self.extractor = (
            EmailIntentExtractor()
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
        email_id = email.get("id")

        # 1. Deduplication check
        if email_id and SignalRepository.exists_message_id(email_id):
            logger.info(
                f"Skipping already processed email ID: {email_id} "
                f"({email.get('subject')})"
            )
            return

        # 2. Rule-based Noise Filter check
        if (
            EmailNoiseFilter
            .is_noise(email)
        ):
            logger.info(
                f"DROP → "
                f"{email['subject']}"
            )
            
            # Save the noise email message ID to avoid processing it again
            if email_id:
                SignalRepository.create_signal(
                    source="email",
                    signal_type="ignore",
                    category="general",
                    importance="ignore",
                    summary=email["subject"],
                    message_id=email_id
                )

            return

        logger.info(
            f"KEEP → "
            f"{email['subject']}"
        )

        # 3. Single-pass comprehensive LLM processing
        try:
            extracted = (
                self.extractor
                .extract_intent(email)
            )

            category = (
                CategoryNormalizer
                .normalize(
                    extracted.get(
                        "intent",
                        "unknown",
                    ),
                    extracted.get(
                        "category",
                        "general",
                    ),
                )
            )

            summary = (
                extracted.get(
                    "summary"
                )
                or email["subject"]
            )

            importance = (
                extracted.get(
                    "priority",
                    "medium",
                )
            )

            signal_type = (
                extracted.get(
                    "intent",
                    "unknown",
                )
            )

            details = (
                extracted.get(
                    "details"
                )
                or {}
            )

            # 3.2 OTP/Ignore check - discard right away
            if signal_type == "otp" or importance == "ignore":
                logger.info(f"OTP/Ignore email discarded: {summary}.")
                return

            # 3.5 Cross-channel duplicate check
            if SignalRepository.is_duplicate_signal(category, signal_type, details, summary):
                logger.info(
                    f"Cross-channel duplicate detected for email: {summary}. Skipping."
                )
                return

            # 4. Store structured signal in the unified 'signals' table
            SignalRepository.create_signal(
                source="email",
                signal_type=signal_type,
                category=category,
                importance=importance,
                summary=summary,
                raw_data=details,
                message_id=email_id,
            )

            # 5. Task Creation if required
            if (
                extracted.get(
                    "action_required",
                    False,
                )
            ):
                TaskRepository.create_task(
                    title=summary,
                    category=category,
                    priority=importance,
                    source="email",
                    due_date=extracted.get(
                        "due_date"
                    ),
                )

            logger.success(
                f"\nProcessed Email ID {email_id}:\n"
                f"Intent: {signal_type}\n"
                f"Category: {category}\n"
                f"Priority: {importance}\n"
                f"Details: {details}\n"
            )

        except Exception as ex:
            logger.error(
                f"Failed to process email ID {email_id}: {ex}"
            )