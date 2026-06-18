class CategoryNormalizer:

    CATEGORY_MAP = {

        # Finance
        "payment_confirmation": "finance",
        "transaction_alert": "finance",
        "financial_transaction": "finance",

        # Shopping
        "delivery_update": "shopping",
        "shopping_order": "shopping",
        "order_confirmation": "shopping",

        # Insurance
        "insurance_reminder": "insurance",

        # Career
        "job_alert": "career",

        # School
        "school_notice": "school",
    }

    @classmethod
    def normalize(
        cls,
        intent_name,
        category,
    ):

        return cls.CATEGORY_MAP.get(
            intent_name,
            category,
        )