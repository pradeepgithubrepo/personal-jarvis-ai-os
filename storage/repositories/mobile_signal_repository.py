from storage.db.database import (
    SessionLocal
)

from storage.models.mobile_signal import (
    MobileSignal
)


class MobileSignalRepository:

    @staticmethod
    def save_signal(
        device_id,
        source,
        sender,
        message,
        timestamp
    ):

        db = SessionLocal()

        try:

            signal = MobileSignal(

                device_id=device_id,

                source=source,

                sender=sender,

                message=message,

                mobile_timestamp=
                    str(timestamp)
            )

            db.add(signal)

            db.commit()

        finally:

            db.close()