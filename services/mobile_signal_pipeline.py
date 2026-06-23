# services/mobile_signal_pipeline.py

from loguru import logger
from storage.repositories.mobile_signal_repository import MobileSignalRepository
from storage.repositories.signal_repository import SignalRepository
from skills.mobile.mobile_noise_filter import MobileNoiseFilter
from skills.mobile.mobile_intent_extractor import MobileIntentExtractor


class MobileSignalPipeline:

    def __init__(self):
        self.extractor = MobileIntentExtractor()

    def run(self):
        """
        Runs the mobile signal structuring pipeline.
        Fetches unprocessed mobile signals, filters out noise,
        extracts intents/categories/details using the local LLM,
        and saves them into the main unified signals table.
        """
        logger.info("Running Mobile Signal LLM Processing Pipeline...")

        try:
            unprocessed = MobileSignalRepository.get_unprocessed_signals(limit=100)
            if not unprocessed:
                logger.info("No unprocessed mobile signals found.")
                return

            logger.info(f"Found {len(unprocessed)} unprocessed mobile signals to process.")

            for msg in unprocessed:
                logger.info(f"Processing Mobile Signal ID {msg.id} from '{msg.sender}' (Source: {msg.source})")

                signal_dict = {
                    "source": msg.source,
                    "sender": msg.sender,
                    "message": msg.message
                }

                # 1. Rule-based Noise Filter check
                if MobileNoiseFilter.is_noise(signal_dict):
                    MobileSignalRepository.mark_signals_processed([msg.id])
                    logger.info(f"Mobile Signal ID {msg.id} dropped as noise.")
                    continue

                # 2. LLM Intent & Detail Extraction
                try:
                    extracted = self.extractor.extract_intent(signal_dict)
                    logger.info(f"LLM Extracted output: {extracted}")
                    
                    category = extracted.get("category", "general")
                    signal_type = extracted.get("intent", "unknown")
                    importance = extracted.get("priority", "medium")
                    summary = extracted.get("summary") or msg.message[:200]
                    details = extracted.get("details", {})

                    # If badminton-related, importance is always low
                    msg_text_lower = (msg.message or "").lower()
                    summary_lower = (summary or "").lower()
                    if "badminton" in msg_text_lower or "badminton" in summary_lower:
                        importance = "low"

                    # 2.3 OTP/Ignore check - discard right away
                    if signal_type == "otp" or importance == "ignore":
                        MobileSignalRepository.mark_signals_processed([msg.id])
                        logger.info(f"OTP/Ignore mobile signal ID {msg.id} discarded.")
                        continue

                    # 2.5 Cross-channel duplicate check
                    if SignalRepository.is_duplicate_signal(category, signal_type, details, summary):
                        MobileSignalRepository.mark_signals_processed([msg.id])
                        logger.info(f"Cross-channel duplicate detected for mobile signal: {summary}. Skipping signal creation.")
                        continue

                    # 3. Store structured signal in the unified 'signals' table
                    SignalRepository.create_signal(
                        source=msg.source,
                        signal_type=signal_type,
                        category=category,
                        importance=importance,
                        summary=summary,
                        raw_data=details
                    )

                    # 3.6 Create task in the tasks table if action required
                    if extracted.get("action_required", False):
                        from storage.repositories.task_repository import TaskRepository
                        TaskRepository.create_task(
                            title=summary,
                            category=category,
                            priority=importance,
                            source=msg.source,
                            due_date=extracted.get("due_date"),
                        )

                    # 4. Mark as processed in the mobile_signals table
                    MobileSignalRepository.mark_signals_processed([msg.id])
                    logger.success(f"Structured and saved mobile signal ID {msg.id}")

                except Exception as ex:
                    logger.error(f"Failed to extract or save mobile signal ID {msg.id}: {ex}")

            logger.info("Mobile Signal LLM Processing Pipeline run complete.")

        except Exception as e:
            logger.error(f"Error running Mobile Signal Pipeline: {e}")
