# src/agents/fyi/importance.py

class FyiImportance:
    """
    Deterministically scores and assigns importance level (LOW, MEDIUM, HIGH)
    for FYI events.
    """

    @staticmethod
    def resolve(event_type: str, signal_summary: str) -> str:
        """
        Returns LOW, MEDIUM, or HIGH.
        """
        summary_lower = signal_summary.lower()

        # 1. High priority events
        if event_type in ("SCHOOL_NOTICE", "KYC_COMPLETED") or "urgent" in summary_lower or "critical" in summary_lower:
            return "HIGH"
        
        # Large refund or high values
        if event_type == "REFUND_RECEIVED" or "refund" in summary_lower:
            return "HIGH"

        # 2. Medium priority events
        if event_type in ("SALARY_CREDITED", "FLIGHT_BOOKED", "HOTEL_CONFIRMED", "CHECKIN_COMPLETED", "MEDICAL_UPDATE"):
            return "MEDIUM"

        # 3. Low priority events
        if event_type in ("SUBSCRIPTION_RENEWED", "SIP_EXECUTED"):
            return "LOW"

        return "MEDIUM"
