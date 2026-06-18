class EmailNoiseFilter:

    IMPORTANT_SENDERS = [

        # Banks
        "hdfcbank.bank.in",
        "alerts.sbi.bank.in",
        "sbicard.com",
        "axis.bank.in",

        # Payments
        "amazonpay.in",
        "cred.club",

        # Shopping
        "flipkart.com",
        "amazon.in",

        # Utilities
        "actcorp.in",
    ]

    IMPORTANT_KEYWORDS = [

        "payment",
        "transaction",
        "credit card",
        "statement",
        "bill",
        "otp",
        "order",
        "delivery",
        "premium due",
        "insurance due",
        "alert",
        "emi",
        "credited",
        "debited",
        "upi",
        "refund",
    ]

    BLOCKED_SENDERS = [

        "substack.com",
        "medium.com",
        "linkedin.com",
        "indeed.com",
        "timesjobs.com",
        "economictimesnews.com",
        "hindustantimes.com",
        "quora.com",
        "glassdoor.com",
    ]

    BLOCKED_SUBJECT_WORDS = [

        "newsletter",
        "digest",
        "recommended",
        "highlights",
        "weekend",
        "weekly",
        "headlines",
        "suggested",
        "trending",
        "top stories",
    ]

    @classmethod
    def is_noise(
        cls,
        email,
    ) -> bool:

        sender = (
            email.get(
                "sender",
                "",
            )
            .lower()
        )

        subject = (
            email.get(
                "subject",
                "",
            )
            .lower()
        )

        score = 0

        # -----------------
        # Sender Signals
        # -----------------

        for sender_rule in (
            cls.IMPORTANT_SENDERS
        ):

            if sender_rule in sender:

                score += 5

        for blocked in (
            cls.BLOCKED_SENDERS
        ):

            if blocked in sender:

                score -= 5

        # -----------------
        # Subject Signals
        # -----------------

        for keyword in (
            cls.IMPORTANT_KEYWORDS
        ):

            if keyword in subject:

                score += 3

        for blocked_word in (
            cls
            .BLOCKED_SUBJECT_WORDS
        ):

            if blocked_word in subject:

                score -= 3

        # -----------------
        # Final Decision
        # -----------------

        return score <= 0