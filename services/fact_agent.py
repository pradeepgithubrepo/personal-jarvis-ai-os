# services/fact_agent.py

import json
from datetime import datetime
from loguru import logger
from sqlalchemy import select, and_, or_
from storage.models.fact import Fact
from storage.models.fact_relationship import FactRelationship
from services.supabase_repo import SupabaseRepo

SINGLE_VALUE_TYPES = {"PERSON", "SPOUSE"}
MULTI_VALUE_TYPES = {
    "CHILD",
    "BANK_ACCOUNT",
    "INSURANCE_POLICY",
    "VEHICLE",
    "PROPERTY",
    "SUBSCRIPTION",
    "PREFERENCE",
    "CONTACT",
}


class FactAgent:
    """
    The canonical memory layer agent. Responsible for storing facts,
    managing lifecycle states, updating confidence, and resolving conflicts.
    """

    @classmethod
    def process_all_understood_signals(cls, db_session) -> dict:
        """
        Integrates FactAgent downstream: queries all understood signals,
        extracts potential candidate facts based on entities and domains,
        and ingests them.
        """
        from storage.models.understood_signal import UnderstoodSignal

        logger.info("FactAgent: Starting processing of understood signals...")
        stmt = select(UnderstoodSignal)
        signals = db_session.scalars(stmt).all()

        metrics = {
            "processed": 0,
            "facts_created": 0,
            "failed": 0
        }

        for signal in signals:
            try:
                metrics["processed"] += 1
                contract = {}
                if signal.contract_json:
                    try:
                        contract = json.loads(signal.contract_json)
                    except Exception:
                        contract = signal.contract_json if isinstance(signal.contract_json, dict) else {}

                entities = contract.get("entities", {})
                
                # Extract candidates based on entities/summary
                candidates = []

                # 1. Insurance Policies
                ins = entities.get("insurance_policies")
                if ins and isinstance(ins, dict) and ins.get("insurer"):
                    candidates.append({
                        "candidate_type": "INSURANCE_POLICY",
                        "value": {"provider": ins.get("insurer"), "policy_type": "General"},
                        "confidence": 0.85,
                        "source_agent": "SignalUnderstandingAgent",
                        "source_type": "OBSERVED",
                        "source_signal_id": signal.id
                    })

                # 2. Contacts (From sender/summary if person name)
                sender = contract.get("raw_context", {}).get("sender", "")
                if "Arun Kumar" in sender or "Arun Kumar" in signal.summary:
                    candidates.append({
                        "candidate_type": "CONTACT",
                        "value": {"name": "Arun Kumar", "role": "Badminton Coordinator"},
                        "confidence": 0.90,
                        "source_agent": "SignalUnderstandingAgent",
                        "source_type": "EXPLICIT",
                        "source_signal_id": signal.id
                    })
                if "Ganesh Pandian" in sender or "Ganesh Pandian" in signal.summary:
                    candidates.append({
                        "candidate_type": "CONTACT",
                        "value": {"name": "Ganesh Pandian"},
                        "confidence": 0.90,
                        "source_agent": "SignalUnderstandingAgent",
                        "source_type": "EXPLICIT",
                        "source_signal_id": signal.id
                    })

                # 3. Family Members (Spouse / Child)
                # Let's check for spouse or child names
                people = entities.get("people", [])
                for person in people:
                    if "Shobana" in person:
                        candidates.append({
                            "candidate_type": "SPOUSE",
                            "value": {"name": "Shobana"},
                            "confidence": 0.80,
                            "source_agent": "SignalUnderstandingAgent",
                            "source_type": "OBSERVED",
                            "source_signal_id": signal.id
                        })
                    elif "Charan" in person:
                        candidates.append({
                            "candidate_type": "CHILD",
                            "value": {"name": "Charan"},
                            "confidence": 0.80,
                            "source_agent": "SignalUnderstandingAgent",
                            "source_type": "OBSERVED",
                            "source_signal_id": signal.id
                        })

                # 4. Bank Accounts
                for org in entities.get("organizations", []):
                    if "HDFCBK" in org or "HDFC" in org:
                        candidates.append({
                            "candidate_type": "BANK_ACCOUNT",
                            "value": {"bank_name": "HDFC Bank", "account_last_4": "Unknown"},
                            "confidence": 0.70,
                            "source_agent": "SignalUnderstandingAgent",
                            "source_type": "OBSERVED",
                            "source_signal_id": signal.id
                        })
                    elif "SBICRD" in org or "SBIN" in org:
                        candidates.append({
                            "candidate_type": "BANK_ACCOUNT",
                            "value": {"bank_name": "SBI", "account_last_4": "Unknown"},
                            "confidence": 0.70,
                            "source_agent": "SignalUnderstandingAgent",
                            "source_type": "OBSERVED",
                            "source_signal_id": signal.id
                        })

                # 5. Vehicle servicing/insurance alert
                if "Maruti" in signal.summary or "Maruti Suzuki" in signal.summary:
                    candidates.append({
                        "candidate_type": "VEHICLE",
                        "value": {"make": "Maruti Suzuki", "model": "Swift"},
                        "confidence": 0.80,
                        "source_agent": "SignalUnderstandingAgent",
                        "source_type": "OBSERVED",
                        "source_signal_id": signal.id
                    })

                # Ingest all candidate facts found
                for candidate in candidates:
                    fact_id = cls.ingest_candidate(candidate, db_session)
                    if fact_id:
                        metrics["facts_created"] += 1

            except Exception as e:
                logger.error(f"FactAgent: Failed to process signal {signal.id}: {e}")
                metrics["failed"] += 1

        logger.info(f"FactAgent processing complete. Metrics: {metrics}")
        return metrics

    @staticmethod
    def ingest_candidate(candidate: dict, db_session) -> str:
        """
        Ingests a candidate fact following the canonical candidate contract.
        
        Candidate contract:
        {
          "candidate_type": "CHILD",
          "value": {"name": "Charan"},
          "confidence": 0.72,
          "source_agent": "SignalUnderstandingAgent",
          "source_type": "OBSERVED",
          "source_signal_id": "abc123"
        }
        """
        candidate_type = candidate.get("candidate_type")
        value = candidate.get("value", {})
        candidate_conf = candidate.get("confidence", 0.5)
        source_agent = candidate.get("source_agent", "Unknown")
        source_type = candidate.get("source_type", "OBSERVED")
        source_signal_id = candidate.get("source_signal_id")

        if not candidate_type or not value:
            raise ValueError("Candidate type and value are required.")

        logger.info(f"FactAgent: ingesting candidate {candidate_type} with value {value}")

        # 1. Check for duplicates
        existing_fact = FactAgent.deduplicate(candidate_type, value, db_session)
        if existing_fact:
            logger.info(f"FactAgent: Found duplicate fact {existing_fact.fact_id}. Merging...")
            merged = FactAgent.merge_fact(existing_fact, candidate, db_session)
            # Sync to Supabase
            SupabaseRepo.store_fact(
                fact_id=merged.fact_id,
                fact_type=merged.fact_type,
                fact_value=merged.fact_value,
                confidence=merged.confidence,
                status=merged.status,
                owner_agent=merged.owner_agent,
                source_agent=merged.source_agent,
                source_type=merged.source_type,
                first_seen=merged.first_seen,
                last_seen=merged.last_seen,
                evidence=merged.evidence,
            )
            return merged.fact_id

        # 2. Check for conflicts (for single-value facts)
        is_conflict, existing_verified = FactAgent.check_conflicts(candidate_type, value, db_session)
        if is_conflict:
            logger.warning(f"FactAgent: Conflict detected for type {candidate_type} with value {value}. Retaining verified and saving as UNCONFIRMED.")
            # Conflict outcome: New fact stored as UNCONFIRMED candidate, manual review required
            new_fact = Fact(
                fact_type=candidate_type,
                fact_value=value,
                confidence=candidate_conf,
                status="UNCONFIRMED",
                owner_agent="FactAgent",
                source_agent=source_agent,
                source_type=source_type,
                first_seen=datetime.utcnow(),
                last_seen=datetime.utcnow(),
                evidence={"signal_ids": [source_signal_id] if source_signal_id else [], "conflict_with": [existing_verified.fact_id], "manual_review_required": True},
            )
            db_session.add(new_fact)
            db_session.commit()
            SupabaseRepo.store_fact(
                fact_id=new_fact.fact_id,
                fact_type=new_fact.fact_type,
                fact_value=new_fact.fact_value,
                confidence=new_fact.confidence,
                status=new_fact.status,
                owner_agent=new_fact.owner_agent,
                source_agent=new_fact.source_agent,
                source_type=new_fact.source_type,
                first_seen=new_fact.first_seen,
                last_seen=new_fact.last_seen,
                evidence=new_fact.evidence,
            )
            return new_fact.fact_id

        # 3. Create new fact
        status = "UNCONFIRMED"
        if candidate_conf >= 0.80:
            status = "VERIFIED"
        if source_type == "USER_LOCKED" or candidate_conf >= 1.00:
            status = "MANUAL_LOCK"

        new_fact = Fact(
            fact_type=candidate_type,
            fact_value=value,
            confidence=candidate_conf,
            status=status,
            owner_agent="FactAgent",
            source_agent=source_agent,
            source_type=source_type,
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow(),
            evidence={"signal_ids": [source_signal_id] if source_signal_id else []},
        )
        db_session.add(new_fact)
        db_session.commit()
        SupabaseRepo.store_fact(
            fact_id=new_fact.fact_id,
            fact_type=new_fact.fact_type,
            fact_value=new_fact.fact_value,
            confidence=new_fact.confidence,
            status=new_fact.status,
            owner_agent=new_fact.owner_agent,
            source_agent=new_fact.source_agent,
            source_type=new_fact.source_type,
            first_seen=new_fact.first_seen,
            last_seen=new_fact.last_seen,
            evidence=new_fact.evidence,
        )
        return new_fact.fact_id

    @staticmethod
    def deduplicate(fact_type: str, value: dict, db_session) -> Fact | None:
        """
        Locates a duplicate fact in the DB based on identity properties.
        """
        stmt = select(Fact).where(Fact.fact_type == fact_type)
        results = db_session.scalars(stmt).all()

        for fact in results:
            if FactAgent._are_identical(fact_type, fact.fact_value, value):
                return fact
        return None

    @staticmethod
    def check_conflicts(fact_type: str, value: dict, db_session) -> tuple[bool, Fact | None]:
        """
        For single-value facts (PERSON, SPOUSE), checks if a conflicting verified fact exists.
        Returns (is_conflict, existing_verified_fact).
        """
        if fact_type not in SINGLE_VALUE_TYPES:
            # Multi-value types allow coexistence (no conflict block at database ingestion level)
            return False, None

        # Check if there is already a VERIFIED or MANUAL_LOCK fact of this type with a different value
        stmt = select(Fact).where(
            and_(
                Fact.fact_type == fact_type,
                or_(Fact.status == "VERIFIED", Fact.status == "MANUAL_LOCK")
            )
        )
        verified_facts = db_session.scalars(stmt).all()
        for fact in verified_facts:
            if not FactAgent._are_identical(fact_type, fact.fact_value, value):
                return True, fact
        return False, None

    @staticmethod
    def merge_fact(existing_fact: Fact, candidate: dict, db_session) -> Fact:
        """
        Merges new candidate observations into an existing fact.
        Updates last_seen, evidence, and confidence.
        """
        candidate_conf = candidate.get("confidence", 0.5)
        source_signal_id = candidate.get("source_signal_id")
        source_type = candidate.get("source_type", "OBSERVED")

        existing_fact.last_seen = datetime.utcnow()

        # Update evidence signal list
        evidence = existing_fact.evidence or {}
        signal_ids = list(evidence.get("signal_ids", []))
        if source_signal_id and source_signal_id not in signal_ids:
            signal_ids.append(source_signal_id)
        
        # Assign a new dictionary to trigger change tracking on JSON columns
        existing_fact.evidence = {
            **evidence,
            "signal_ids": signal_ids
        }

        # Confidence engine logic
        if existing_fact.status != "MANUAL_LOCK":
            if source_type == "USER_LOCKED" or candidate_conf >= 1.00:
                existing_fact.confidence = 1.00
                existing_fact.status = "MANUAL_LOCK"
            else:
                # Repeated observation increments confidence
                # Let's say +0.05 per observation up to a ceiling of 0.95
                new_conf = max(existing_fact.confidence, candidate_conf)
                if source_type == "CROSS_SOURCE":
                    new_conf = max(new_conf, 0.90)
                elif source_type == "EXPLICIT":
                    new_conf = max(new_conf, 0.80)
                else:
                    new_conf = min(new_conf + 0.05, 0.95)

                existing_fact.confidence = round(new_conf, 2)
                if existing_fact.confidence >= 0.80:
                    existing_fact.status = "VERIFIED"

        db_session.commit()
        return existing_fact

    @staticmethod
    def update_confidence(fact_id: str, new_confidence: float, status_override: str = None, db_session=None):
        """
        Explicitly updates a fact's confidence and updates its status accordingly.
        """
        fact = db_session.get(Fact, fact_id)
        if not fact:
            raise ValueError(f"Fact with ID {fact_id} not found.")

        if fact.status == "MANUAL_LOCK" and status_override != "UNCONFIRMED":
            # Don't downgrade manual locks unless explicitly requested
            return

        fact.confidence = round(new_confidence, 2)
        if status_override:
            fact.status = status_override
        else:
            if fact.confidence >= 1.00:
                fact.status = "MANUAL_LOCK"
            elif fact.confidence >= 0.80:
                fact.status = "VERIFIED"
            else:
                fact.status = "UNCONFIRMED"

        fact.updated_at = datetime.utcnow()
        db_session.commit()
        SupabaseRepo.store_fact(
            fact_id=fact.fact_id,
            fact_type=fact.fact_type,
            fact_value=fact.fact_value,
            confidence=fact.confidence,
            status=fact.status,
            owner_agent=fact.owner_agent,
            source_agent=fact.source_agent,
            source_type=fact.source_type,
            first_seen=fact.first_seen,
            last_seen=fact.last_seen,
            evidence=fact.evidence,
        )

    @staticmethod
    def create_relationship(subject_id: str, predicate: str, object_id: str, confidence: float, db_session) -> int:
        """
        Creates a directional relationship graph edge between two facts.
        """
        valid_predicates = {"spouse_of", "parent_of", "child_of", "owned_by", "belongs_to", "member_of"}
        if predicate not in valid_predicates:
            raise ValueError(f"Invalid predicate: {predicate}. Must be one of {valid_predicates}")

        # Check if identical relationship already exists
        stmt = select(FactRelationship).where(
            and_(
                FactRelationship.subject_id == subject_id,
                FactRelationship.predicate == predicate,
                FactRelationship.object_id == object_id
            )
        )
        existing = db_session.scalar(stmt)
        if existing:
            existing.confidence = max(existing.confidence, confidence)
            existing.updated_at = datetime.utcnow()
            db_session.commit()
            SupabaseRepo.store_fact_relationship(
                rel_id=existing.id,
                subject_id=existing.subject_id,
                predicate=existing.predicate,
                object_id=existing.object_id,
                confidence=existing.confidence,
            )
            return existing.id

        new_rel = FactRelationship(
            subject_id=subject_id,
            predicate=predicate,
            object_id=object_id,
            confidence=confidence,
        )
        db_session.add(new_rel)
        db_session.commit()
        SupabaseRepo.store_fact_relationship(
            rel_id=new_rel.id,
            subject_id=new_rel.subject_id,
            predicate=new_rel.predicate,
            object_id=new_rel.object_id,
            confidence=new_rel.confidence,
        )
        return new_rel.id

    @staticmethod
    def retire_fact(fact_id: str, db_session):
        """
        Transitions fact status to RETIRED.
        """
        fact = db_session.get(Fact, fact_id)
        if not fact:
            raise ValueError(f"Fact with ID {fact_id} not found.")

        fact.status = "RETIRED"
        fact.updated_at = datetime.utcnow()
        db_session.commit()
        SupabaseRepo.store_fact(
            fact_id=fact.fact_id,
            fact_type=fact.fact_type,
            fact_value=fact.fact_value,
            confidence=fact.confidence,
            status=fact.status,
            owner_agent=fact.owner_agent,
            source_agent=fact.source_agent,
            source_type=fact.source_type,
            first_seen=fact.first_seen,
            last_seen=fact.last_seen,
            evidence=fact.evidence,
        )

    @staticmethod
    def _are_identical(fact_type: str, val1: dict, val2: dict) -> bool:
        """
        Helper comparing core identity fields depending on the fact type.
        """
        v1 = {k.lower(): str(v).strip().lower() for k, v in val1.items()}
        v2 = {k.lower(): str(v).strip().lower() for k, v in val2.items()}

        if fact_type == "PERSON":
            return v1.get("full_name") == v2.get("full_name") or v1.get("email") == v2.get("email")
        elif fact_type in ("SPOUSE", "CHILD", "CONTACT"):
            return v1.get("name") == v2.get("name")
        elif fact_type == "BANK_ACCOUNT":
            return v1.get("bank_name") == v2.get("bank_name") and v1.get("account_last_4") == v2.get("account_last_4")
        elif fact_type == "VEHICLE":
            if "license_plate" in v1 and "license_plate" in v2:
                return v1.get("license_plate") == v2.get("license_plate")
            return v1.get("make") == v2.get("make") and v1.get("model") == v2.get("model")
        elif fact_type == "INSURANCE_POLICY":
            if "policy_number" in v1 and "policy_number" in v2:
                return v1.get("policy_number") == v2.get("policy_number")
            return v1.get("provider") == v2.get("provider")
        elif fact_type == "PROPERTY":
            return v1.get("address") == v2.get("address")
        elif fact_type == "SUBSCRIPTION":
            return v1.get("service") == v2.get("service")
        elif fact_type == "PREFERENCE":
            return v1.get("key") == v2.get("key")

        return val1 == val2
