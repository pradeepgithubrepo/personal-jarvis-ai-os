# src/agents/fyi/categorizer.py

class FyiCategorizer:
    """
    Resolves the FYI category and event type based on intent domains,
    entities, and signal summary keywords.
    """

    @staticmethod
    def resolve(signal, contract_json: dict) -> tuple[str, str]:
        """
        Returns (category, event_type).
        """
        summary_lower = signal.summary.lower()
        domains = contract_json.get("domains", [])
        primary_domain = domains[0].upper() if domains else "GENERAL"

        # 1. Financial FYI
        if primary_domain == "FINANCE" or "salary" in summary_lower or "credited" in summary_lower or "refund" in summary_lower or "sip" in summary_lower or "renewed" in summary_lower:
            category = "FINANCIAL"
            if "salary" in summary_lower:
                event_type = "SALARY_CREDITED"
            elif "refund" in summary_lower:
                event_type = "REFUND_RECEIVED"
            elif "sip" in summary_lower:
                event_type = "SIP_EXECUTED"
            elif "renewed" in summary_lower or "subscription" in summary_lower:
                event_type = "SUBSCRIPTION_RENEWED"
            else:
                event_type = "ACCOUNT_CREDITED"
            return category, event_type

        # 2. Travel FYI
        if primary_domain == "TRAVEL" or "flight" in summary_lower or "hotel" in summary_lower or "checkin" in summary_lower or "booking" in summary_lower:
            category = "TRAVEL"
            if "flight" in summary_lower:
                event_type = "FLIGHT_BOOKED"
            elif "hotel" in summary_lower:
                event_type = "HOTEL_CONFIRMED"
            elif "checkin" in summary_lower:
                event_type = "CHECKIN_COMPLETED"
            else:
                event_type = "TRAVEL_BOOKING_CONFIRMED"
            return category, event_type

        # 3. Family FYI
        if primary_domain == "EDUCATION" or "school" in summary_lower or "parent" in summary_lower or "meeting" in summary_lower or "medical" in summary_lower or "doctor" in summary_lower:
            category = "FAMILY"
            if "school" in summary_lower or "parent" in summary_lower:
                event_type = "SCHOOL_NOTICE"
            elif "medical" in summary_lower or "doctor" in summary_lower or "refill" in summary_lower:
                event_type = "MEDICAL_UPDATE"
            else:
                event_type = "FAMILY_EVENT"
            return category, event_type

        # 4. System FYI
        if "kyc" in summary_lower or "profile" in summary_lower or "restored" in summary_lower or "outage" in summary_lower:
            category = "SYSTEM"
            if "kyc" in summary_lower:
                event_type = "KYC_COMPLETED"
            elif "restored" in summary_lower or "up" in summary_lower:
                event_type = "SERVICE_RESTORED"
            else:
                event_type = "ACCOUNT_UPDATED"
            return category, event_type

        # Default fallback
        return "SYSTEM", "GENERAL_FYI"
