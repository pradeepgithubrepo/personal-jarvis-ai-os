import threading
import time

import uvicorn
from fastapi import FastAPI
from loguru import logger

from api.routes.health import (
    router as health_router
)

from api.routes.mobile_sync import (
    router as mobile_sync_router
)

from app.shutdown import shutdown
from app.startup import startup


app = FastAPI(
    title="Jarvis AI OS",
)

app.include_router(
    health_router
)

app.include_router(
    mobile_sync_router
)


def run_runtime():

    logger.info(
        "Jarvis Runtime Starting..."
    )

    scheduler = startup()

    logger.success(
        "Jarvis Runtime Healthy"
    )

    try:

        while True:
            time.sleep(1)

    except KeyboardInterrupt:

        logger.warning(
            "Shutdown signal received"
        )

    finally:

        shutdown(
            scheduler
        )


def main():

    runtime_thread = threading.Thread(
        target=run_runtime,
        daemon=True,
    )

    runtime_thread.start()

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
    )


if __name__ == "__main__":
    main()