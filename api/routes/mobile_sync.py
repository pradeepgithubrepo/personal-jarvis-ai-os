# api/routes/mobile_sync.py

from fastapi import APIRouter

from api.schemas.mobile_sync import (
    SyncRequest
)

from storage.repositories.mobile_signal_repository import (
    MobileSignalRepository
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

        MobileSignalRepository.save_signal(

            device_id=
                request.device_id,

            source=
                signal.source,

            sender=
                signal.sender,

            message=
                signal.message,

            timestamp=
                signal.timestamp
        )
