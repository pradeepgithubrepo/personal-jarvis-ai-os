class EmailNoiseFilter:

    IMPORTANT_SENDERS = [
        "hdfcbank.bank.in",
        "alerts.sbi.bank.in",
        "sbicard.com",
        "axis.bank.in",
        "amazonpay.in",
        "cred.club",
        "flipkart.com",
        "amazon.in",
        "iciciprulife.com",
        "otp",
        "bank",
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
        "premium",
        "insurance",
        "due",
        "alert",
        "emi",
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
    ]

    @classmethod
    def is_noise(
        cls,
        email,
    ) -> bool:

        sender = (
            email["sender"]
            .lower()
        )

        subject = (
            email["subject"]
            .lower()
        )

        # -----------------
        # HARD BLOCK
        # -----------------
        for blocked in (
            cls.BLOCKED_SENDERS
        ):
            if blocked in sender:
                return True

        for word in (
            cls
            .BLOCKED_SUBJECT_WORDS
        ):
            if word in subject:
                return True

        # -----------------
        # HARD KEEP
        # -----------------
        for sender_rule in (
            cls
            .IMPORTANT_SENDERS
        ):
            if sender_rule in sender:
                return False

        for keyword in (
            cls
            .IMPORTANT_KEYWORDS
        ):
            if keyword in subject:
                return False

        # -----------------
        # DEFAULT
        # -----------------
        return True