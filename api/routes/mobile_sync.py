# api/routes/mobile_sync.py

from fastapi import APIRouter

from api.schemas.mobile_sync import (
    SyncRequest
)

router = APIRouter(
    prefix="/mobile",
    tags=["Mobile Sync"]
)


@router.get(
    "/health"
)
async def health():

    return {
        "status": "online"
    }


@router.post(
    "/signals"
)
async def sync_signals(
    request: SyncRequest
):

    print(
        f"Received "
        f"{len(request.signals)} "
        f"signals from "
        f"{request.device_id}"
    )

    for signal in request.signals:

        print(
            signal.model_dump()
        )

    return {

        "status": "success",

        "received":
            len(request.signals)
    }
