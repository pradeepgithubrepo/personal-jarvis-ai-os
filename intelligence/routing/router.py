from loguru import logger

from configs.constants import TaskType
from intelligence.cloud.cloud_llm import (
    CloudLLM,
)
from intelligence.local.local_llm import (
    LocalLLM,
)


class IntelligenceRouter:

    def __init__(self):
        self.local_llm = LocalLLM()
        self.cloud_llm = CloudLLM()

    def ask(
        self,
        prompt: str,
        task_type: str,
        ) -> str:

        logger.info(
            f"Routing task: {task_type}"
        )

        from services.context_provider import ContextProvider
        context_prompt = ContextProvider.get_context_prompt()
        full_prompt = context_prompt + prompt

        local_tasks = [
            TaskType.EXPENSE,
            TaskType.EMAIL,
            TaskType.TODO,
            TaskType.ROUTING,
        ]

        cloud_tasks = [
            TaskType.LEARNING,
            TaskType.SUMMARY,
            TaskType.REASONING,
        ]

        if task_type in local_tasks:
            logger.info(
                "Using LOCAL intelligence"
            )

            return self.local_llm.ask(
                full_prompt
            )

        if task_type in cloud_tasks:
            logger.info(
                "Using CLOUD intelligence"
            )

            return self.cloud_llm.ask(
                full_prompt
            )

        logger.warning(
            "Unknown task type. "
            "Defaulting to local."
        )

        return self.local_llm.ask(
            full_prompt
        )