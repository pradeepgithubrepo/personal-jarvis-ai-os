"""
src/intelligence/contracts/contract_validator.py

Contract validator for Jarvis V2 Phase 2B.

Responsibilities:
- Validate schema (all required fields present)
- Validate enums (signal_type must be in SignalType)
- Validate confidence ranges [0.0, 1.0]
- Validate importance ranges [0.0, 1.0]
- Validate candidate flag consistency with signal_type
- Validate contract_version = 1

Contracts failing validation are rejected, logged, and audited.
Invalid contracts must NEVER be dispatched downstream.

Build Constitution: BC-5
"""
from __future__ import annotations

from dataclasses import dataclass, field
from loguru import logger

from src.intelligence.contracts.contract_schema import (
    CONTRACT_VERSION,
    SignalType,
    CanonicalContract,
    ContractValidationError,
)


@dataclass
class ContractValidationResult:
    """Result of validating a contract."""
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    contract: CanonicalContract | None = None

    def raise_if_invalid(self):
        """Raise ContractValidationError if not valid."""
        if not self.valid:
            raise ContractValidationError(errors=self.errors)


class ContractValidator:
    """
    Validates canonical contracts produced by the SUA.

    Usage:
        result = ContractValidator.validate(contract_dict)
        result.raise_if_invalid()  # raises ContractValidationError if invalid
    """

    # Required top-level fields
    REQUIRED_FIELDS = [
        "contract_version",
        "signal_type",
        "importance",
        "confidence",
        "summary",
        "entities",
        "memory_candidate",
        "requires_action",
        "financial_candidate",
        "fact_candidate",
        "fyi_candidate",
        "noise_candidate",
    ]

    @classmethod
    def validate(
        cls,
        contract: dict,
        signal_id: str | None = None,
    ) -> ContractValidationResult:
        """
        Validate a contract dict.

        Args:
            contract: The contract_json dict from understood_signals.
            signal_id: Optional understood_signal_id for audit logging.

        Returns:
            ContractValidationResult with valid=True/False, errors, warnings.
        """
        errors: list[str] = []
        warnings: list[str] = []

        if not isinstance(contract, dict):
            errors.append(f"Contract must be a dict, got {type(contract).__name__}")
            result = ContractValidationResult(valid=False, errors=errors)
            cls._log_result(result, signal_id)
            return result

        # 1. Check required fields
        for f in cls.REQUIRED_FIELDS:
            if f not in contract:
                errors.append(f"Missing required field: '{f}'")

        if errors:
            # Can't continue validation without required fields
            result = ContractValidationResult(valid=False, errors=errors, warnings=warnings)
            cls._log_result(result, signal_id)
            return result

        # 2. Validate contract_version
        cv = contract.get("contract_version")
        if cv != CONTRACT_VERSION:
            errors.append(f"Unsupported contract_version: {cv!r}. Expected {CONTRACT_VERSION}.")

        # 3. Validate signal_type enum
        signal_type = contract.get("signal_type")
        valid_types = SignalType.values()
        if signal_type not in valid_types:
            errors.append(
                f"Invalid signal_type: {signal_type!r}. Must be one of {valid_types}."
            )
        else:
            # 4. Validate candidate flag consistency
            flag_errors = cls._validate_candidate_flags(contract, signal_type)
            errors.extend(flag_errors)

        # 5. Validate importance range
        importance = contract.get("importance")
        if not isinstance(importance, (int, float)):
            errors.append(f"'importance' must be a float, got {type(importance).__name__}")
        elif not (0.0 <= float(importance) <= 1.0):
            errors.append(f"'importance' must be in [0.0, 1.0], got {importance}")

        # 6. Validate confidence range
        confidence = contract.get("confidence")
        if not isinstance(confidence, (int, float)):
            errors.append(f"'confidence' must be a float, got {type(confidence).__name__}")
        elif not (0.0 <= float(confidence) <= 1.0):
            errors.append(f"'confidence' must be in [0.0, 1.0], got {confidence}")

        # 7. Validate summary
        summary = contract.get("summary", "")
        if not isinstance(summary, str) or not summary.strip():
            errors.append("'summary' must be a non-empty string")
        elif len(summary) > 500:
            warnings.append(f"'summary' exceeds recommended 500 chars ({len(summary)} chars)")

        # 8. Validate entities is a list
        entities = contract.get("entities")
        if not isinstance(entities, list):
            errors.append(f"'entities' must be a list, got {type(entities).__name__}")

        # Build result
        valid = len(errors) == 0
        canonical = None
        if valid:
            try:
                canonical = CanonicalContract.from_dict(contract)
            except Exception as e:
                errors.append(f"Failed to construct CanonicalContract: {e}")
                valid = False

        result = ContractValidationResult(
            valid=valid,
            errors=errors,
            warnings=warnings,
            contract=canonical,
        )
        cls._log_result(result, signal_id)
        return result

    @classmethod
    def _validate_candidate_flags(cls, contract: dict, signal_type: str) -> list[str]:
        """
        Validate that candidate flags are consistent with signal_type.

        Rules:
          financial_candidate == (signal_type == "FINANCIAL")
          fact_candidate      == False
          fyi_candidate       == (signal_type == "FYI")
          noise_candidate     == (signal_type == "NOISE")
          requires_action     == (signal_type == "ACTION")
          memory_candidate    == (signal_type in {ACTION, FYI})
        """
        errors = []

        # Strict flags: exactly one classification flag must match signal_type
        strict_flags = {
            "financial_candidate": (signal_type == SignalType.FINANCIAL),
            "fact_candidate": False,
            "fyi_candidate": (signal_type == SignalType.FYI),
            "noise_candidate": (signal_type == SignalType.NOISE),
            "requires_action": (signal_type == SignalType.ACTION),
        }

        for flag, expected_value in strict_flags.items():
            actual = contract.get(flag)
            if not isinstance(actual, bool):
                errors.append(f"'{flag}' must be a boolean, got {type(actual).__name__}")
            elif actual != expected_value:
                errors.append(
                    f"Flag mismatch: '{flag}' is {actual} but signal_type={signal_type!r} "
                    f"requires it to be {expected_value}."
                )

        # memory_candidate: must be True when signal_type is ACTION/FYI.
        # FINANCIAL and NOISE signals MAY have memory_candidate=True (triggers fyi_agent routing).
        memory_candidate = contract.get("memory_candidate")
        if not isinstance(memory_candidate, bool):
            errors.append(f"'memory_candidate' must be a boolean, got {type(memory_candidate).__name__}")
        elif signal_type in {SignalType.ACTION, SignalType.FYI}:
            if not memory_candidate:
                errors.append(
                    f"Flag mismatch: 'memory_candidate' must be True for signal_type={signal_type!r}."
                )

        return errors

    @classmethod
    def _log_result(cls, result: ContractValidationResult, signal_id: str | None):
        """Log validation result with structured context."""
        if result.valid:
            if result.warnings:
                logger.warning(
                    f"Contract validated with warnings | signal_id={signal_id} | "
                    f"warnings={result.warnings}"
                )
            else:
                logger.debug(f"Contract validated successfully | signal_id={signal_id}")
        else:
            logger.error(
                f"Contract validation FAILED | signal_id={signal_id} | "
                f"errors={result.errors}"
            )
