# storage/repositories/classification_cache_repository.py

import json
from loguru import logger
from storage.db.database import SessionLocal
from storage.models.classification_cache import ClassificationCache

class ClassificationCacheRepository:

    @staticmethod
    def get(cache_key: str) -> dict | None:
        """
        Retrieves a cached classification result by its key.
        """
        if not cache_key:
            return None
        session = SessionLocal()
        try:
            record = session.query(ClassificationCache).filter(
                ClassificationCache.cache_key == cache_key
            ).first()
            if record:
                try:
                    return json.loads(record.result_json)
                except Exception as e:
                    logger.error(f"Failed to parse classification cache JSON for key {cache_key}: {e}")
                    return None
            return None
        except Exception as e:
            logger.error(f"Error reading classification cache: {e}")
            return None
        finally:
            session.close()

    @staticmethod
    def set(cache_key: str, result_dict: dict) -> bool:
        """
        Saves a classification result into the cache.
        """
        if not cache_key or not result_dict:
            return False
        session = SessionLocal()
        try:
            record = ClassificationCache(
                cache_key=cache_key,
                result_json=json.dumps(result_dict)
            )
            session.merge(record)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save key {cache_key} to classification cache: {e}")
            return False
        finally:
            session.close()
