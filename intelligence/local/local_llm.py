from loguru import logger
from ollama import Client

from configs.settings import settings


class LocalLLM:

    def __init__(self):
        self.client = Client(
            host=settings.ollama_url
        )
        self.model = settings.local_model

    def health_check(self) -> bool:
        try:
            models = self.client.list()

            available_models = [
                model.model
                for model in models.models
            ]

            if self.model in available_models:
                logger.success(
                    f"Local model ready: {self.model}"
                )
                return True

            logger.error(
                f"Model not found: {self.model}"
            )
            return False

        except Exception as ex:
            logger.error(
                f"Ollama unavailable: {ex}"
            )
            return False
    
    def ask(self, prompt: str) -> str:
        try:
            response = self.client.chat(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )

            return response.message.content

        except Exception as ex:
            logger.error(
                f"Local inference failed: {ex}"
            )
            raise