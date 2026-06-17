class EmailScoringEngine:

    HIGH_PRIORITY_KEYWORDS = [
        "payment",
        "transaction",
        "credit card",
        "statement",
        "bill",
        "otp",
        "premium",
        "insurance",
        "due",
        "alert",
        "emi",
        "failed",
        "successful",
    ]

    NEGATIVE_KEYWORDS = [
        "opportunity",
        "wealth",
        "grow",
        "investment",
        "returns",
        "market",
        "mutual fund",
        "newsletter",
        "offer",
        "discount",
        "special",
        "exclusive",
        ]

    MEDIUM_PRIORITY_KEYWORDS = [
        "order",
        "delivery",
        "out for delivery",
        "placed",
        "dispatched",
        "shipped",
    ]

    LOW_PRIORITY_KEYWORDS = [
        "offer",
        "discount",
        "wealth",
        "investment",
        "fund",
        "newsletter",
    ]

    @classmethod
    def score_email(
        cls,
        email,
    ):

        score = 0

        content = (
            (
                email["subject"]
                + " "
                + email["snippet"]
                + " "
                + email["body"]
            )
            .lower()
        )

        # --------------------
        # High priority
        # --------------------
        for keyword in (
            cls
            .HIGH_PRIORITY_KEYWORDS
        ):

            if keyword in content:
                score += 10

        # --------------------
        # Medium priority
        # --------------------
        for keyword in (
            cls
            .MEDIUM_PRIORITY_KEYWORDS
        ):

            if keyword in content:
                score += 5

        # --------------------
        # Low priority
        # --------------------
        for keyword in (
            cls
            .LOW_PRIORITY_KEYWORDS
        ):

            if keyword in content:
                score -= 2
        

        for keyword in (
            cls.NEGATIVE_KEYWORDS
        ):

            if keyword in content:
                score -= 10
        # --------------------
        # Final bucket
        # --------------------
        if score >= 15:
            priority = "HIGH"

        elif score >= 5:
            priority = "MEDIUM"

        elif score > 0:
            priority = "LOW"

        else:
            priority = "IGNORE"

        return {
            "score": score,
            "priority": priority,
        }