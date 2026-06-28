# tests/test_fact_agent.py

import sys
import os
from datetime import datetime
from unittest.mock import patch, MagicMock
from loguru import logger

# Add root folder to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import initialize_database, SessionLocal
from storage.models.fact import Fact
from storage.models.fact_relationship import FactRelationship
from storage.models.understood_signal import UnderstoodSignal
from services.fact_agent import FactAgent


def run_fact_agent_tests():
    logger.info("Initializing database for Fact Agent tests...")
    initialize_database()

    db = SessionLocal()
    try:
        # Clear old test facts and relationships
        db.query(FactRelationship).delete()
        db.query(Fact).delete()
        db.query(UnderstoodSignal).delete()
        db.commit()

        # Mock Supabase Repo writes to avoid network requests during agent tests
        mock_supabase_repo = MagicMock()
        mock_supabase_repo.store_fact.return_value = True
        mock_supabase_repo.store_fact_relationship.return_value = True

        with patch("services.fact_agent.SupabaseRepo", mock_supabase_repo):

            # Test Case 1: Fact Ingestion and Creation
            logger.info("Test Case 1: Ingesting a new child candidate...")
            candidate_child = {
                "candidate_type": "CHILD",
                "value": {"name": "Charan"},
                "confidence": 0.85,
                "source_agent": "SignalUnderstandingAgent",
                "source_type": "OBSERVED",
                "source_signal_id": "sig-123"
            }
            fact_id_1 = FactAgent.ingest_candidate(candidate_child, db)
            assert fact_id_1 is not None, "Expected fact_id to be returned"
            
            fact_1 = db.get(Fact, fact_id_1)
            assert fact_1 is not None, "Fact should be persisted in local SQLite database"
            assert fact_1.fact_type == "CHILD"
            assert fact_1.fact_value["name"] == "Charan"
            assert fact_1.status == "VERIFIED", f"Expected status VERIFIED, got {fact_1.status}"
            assert fact_1.confidence == 0.85
            logger.success("Test Case 1: Passed.")

            # Test Case 2: Deduplication and Merging
            logger.info("Test Case 2: Ingesting the duplicate child fact to check deduplication...")
            candidate_dup = {
                "candidate_type": "CHILD",
                "value": {"name": "Charan"},
                "confidence": 0.80,
                "source_agent": "SignalUnderstandingAgent",
                "source_type": "CROSS_SOURCE",
                "source_signal_id": "sig-456"
            }
            fact_id_2 = FactAgent.ingest_candidate(candidate_dup, db)
            assert fact_id_1 == fact_id_2, "Expected duplicate fact ingestion to merge and return same fact_id"
            
            db.refresh(fact_1)
            assert fact_1.confidence == 0.90, f"Expected merged confidence to be boosted to 0.90 (CROSS_SOURCE), got {fact_1.confidence}"
            assert "sig-456" in fact_1.evidence["signal_ids"], "Expected new signal ID to be merged into evidence list"
            logger.success("Test Case 2: Passed.")

            # Test Case 3: Single-Value Conflict Handling
            logger.info("Test Case 3: Testing conflict resolution on single-value spouse facts...")
            candidate_spouse_1 = {
                "candidate_type": "SPOUSE",
                "value": {"name": "Shobana"},
                "confidence": 0.90,
                "source_agent": "SignalUnderstandingAgent",
                "source_type": "EXPLICIT",
                "source_signal_id": "sig-789"
            }
            spouse_id_1 = FactAgent.ingest_candidate(candidate_spouse_1, db)
            spouse_1 = db.get(Fact, spouse_id_1)
            assert spouse_1.status == "VERIFIED"

            # Ingest conflicting spouse name
            candidate_spouse_conflict = {
                "candidate_type": "SPOUSE",
                "value": {"name": "OtherName"},
                "confidence": 0.85,
                "source_agent": "SignalUnderstandingAgent",
                "source_type": "OBSERVED",
                "source_signal_id": "sig-999"
            }
            conflict_id = FactAgent.ingest_candidate(candidate_spouse_conflict, db)
            assert conflict_id != spouse_id_1, "Conflicting spouse must be created as a separate Fact"
            
            conflict_fact = db.get(Fact, conflict_id)
            assert conflict_fact.status == "UNCONFIRMED", "Conflicting candidate must be kept UNCONFIRMED"
            assert conflict_fact.evidence.get("manual_review_required") is True, "Expected conflict fact to flag manual review"
            logger.success("Test Case 3: Passed.")

            # Test Case 4: Fact Relationship Edge Creation
            logger.info("Test Case 4: Linking user Person to Child...")
            user_fact = Fact(
                fact_type="PERSON",
                fact_value={"full_name": "Pradeep"},
                confidence=1.0,
                status="MANUAL_LOCK",
                source_agent="Manual",
                source_type="USER_LOCKED"
            )
            db.add(user_fact)
            db.commit()

            rel_id = FactAgent.create_relationship(
                subject_id=user_fact.fact_id,
                predicate="parent_of",
                object_id=fact_1.fact_id,
                confidence=0.95,
                db_session=db
            )
            assert rel_id is not None
            rel = db.get(FactRelationship, rel_id)
            assert rel is not None
            assert rel.subject_id == user_fact.fact_id
            assert rel.predicate == "parent_of"
            assert rel.object_id == fact_1.fact_id
            logger.success("Test Case 4: Passed.")

            # Test Case 5: Confidence Updates and Lifecycle Transitions
            logger.info("Test Case 5: Testing manual retirement of a fact...")
            FactAgent.retire_fact(fact_1.fact_id, db)
            db.refresh(fact_1)
            assert fact_1.status == "RETIRED", f"Expected status to transition to RETIRED, got {fact_1.status}"
            logger.success("Test Case 5: Passed.")

            # Test Case 6: Open-ended Understood Signal Processing Integration
            logger.info("Test Case 6: Testing signal extraction integration...")
            # Add a mock understood signal containing insurance details in contract_json
            mock_contract = {
                "entities": {
                    "people": ["Shobana"],
                    "insurance_policies": {"insurer": "Acko General Insurance"},
                    "organizations": ["HDFCBK"]
                },
                "raw_context": {
                    "sender": "HDFCBK",
                    "source": "sms"
                }
            }
            import json
            mock_sig = UnderstoodSignal(
                id="mock-sig-101",
                qualified_signal_id=12,
                raw_signal_id="raw-12",
                signal_type="general",
                importance="MEDIUM",
                confidence=1.0,
                summary="Policy alert from Acko",
                processing_path="RULE_ENGINE",
                llm_model_used="none",
                contract_json=json.dumps(mock_contract)
            )
            db.add(mock_sig)
            db.commit()

            metrics = FactAgent.process_all_understood_signals(db)
            assert metrics["processed"] > 0
            assert metrics["facts_created"] > 0
            
            # Verify that BANK_ACCOUNT and INSURANCE_POLICY were extracted and persisted
            db_facts = db.query(Fact).all()
            fact_types = [f.fact_type for f in db_facts]
            assert "INSURANCE_POLICY" in fact_types, "Expected extracted INSURANCE_POLICY fact to exist in database"
            assert "BANK_ACCOUNT" in fact_types, "Expected extracted BANK_ACCOUNT fact to exist in database"
            logger.success("Test Case 6: Passed.")

        logger.success("ALL LOCAL FACT AGENT TESTS PASSED SUCCESSFULLY!")

    finally:
        # Cleanup
        db.query(FactRelationship).delete()
        db.query(Fact).delete()
        db.query(UnderstoodSignal).delete()
        db.commit()
        db.close()


if __name__ == "__main__":
    run_fact_agent_tests()
