import socket
from datetime import datetime
from loguru import logger
from typing import Optional

from storage.db.database import SessionLocal
from storage.models.scheduler_heartbeat import SchedulerHeartbeat


class SchedulerHeartbeatRepository:

    @staticmethod
    def start_heartbeat(task_name: str) -> Optional[int]:
        db = SessionLocal()
        try:
            machine_name = socket.gethostname() or "unknown"
            heartbeat = SchedulerHeartbeat(
                task_name=task_name,
                execution_start=datetime.utcnow(),
                status="STARTED",
                machine_name=machine_name,
                created_at=datetime.utcnow(),
            )
            db.add(heartbeat)
            db.commit()
            db.refresh(heartbeat)
            logger.info(f"Scheduler heartbeat STARTED for task: {task_name} (ID: {heartbeat.id})")
            return heartbeat.id
        except Exception as ex:
            logger.error(f"Failed to start scheduler heartbeat: {ex}")
            db.rollback()
            return None
        finally:
            db.close()

    @staticmethod
    def complete_heartbeat(heartbeat_id: int, status: str = "COMPLETED") -> None:
        if not heartbeat_id:
            return
        db = SessionLocal()
        try:
            heartbeat = db.query(SchedulerHeartbeat).filter(SchedulerHeartbeat.id == heartbeat_id).first()
            if heartbeat:
                now = datetime.utcnow()
                heartbeat.execution_end = now
                duration = int((now - heartbeat.execution_start).total_seconds())
                heartbeat.duration_seconds = duration
                heartbeat.status = status
                db.commit()
                logger.info(f"Scheduler heartbeat {status} for ID: {heartbeat_id} (Duration: {duration}s)")
            else:
                logger.warning(f"Heartbeat record with ID {heartbeat_id} not found for completion")
        except Exception as ex:
            logger.error(f"Failed to complete scheduler heartbeat: {ex}")
            db.rollback()
        finally:
            db.close()


class HeartbeatHandle:
    def __init__(self, heartbeat_id: int):
        self.id = heartbeat_id
        self.status = "COMPLETED"


from contextlib import contextmanager

@contextmanager
def scheduler_heartbeat_context(task_name: str):
    hb_id = SchedulerHeartbeatRepository.start_heartbeat(task_name)
    handle = HeartbeatHandle(hb_id) if hb_id else None
    try:
        yield handle
        if handle and handle.id:
            SchedulerHeartbeatRepository.complete_heartbeat(handle.id, handle.status)
    except Exception as e:
        if handle and handle.id:
            status_str = f"FAILED: {str(e)}"[:50]
            SchedulerHeartbeatRepository.complete_heartbeat(handle.id, status_str)
        raise e

