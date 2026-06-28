# storage/seeds/bank_accounts_seed.py
"""
Pre-seeded bank accounts for internal transfer detection.
These represent the user's known accounts at Indian banks.
Add or remove accounts as needed — the Financial Agent uses these
to validate both legs of a transfer pair.
"""

BANK_ACCOUNTS_SEED = [
    {
        "bank_name": "HDFC Bank",
        "ifsc_prefix": "HDFC",
        "account_number_masked": "xx3221",
        "account_type": "savings",
        "sender_aliases": [
            "JM-HDFCBK-S", "CP-HDFCBK-S", "VD-HDFCBK-S", "AD-HDFCBK-S",
            "JX-HDFCBK-S", "VM-HDFCBK-S", "AX-HDFCBK-S", "JD-HDFCBK-T",
            "HDFCBK", "hdfcbk"
        ],
        "receiver_aliases": [
            "hdfc bank", "hdfc a/c", "hdfc account", "a/c xx3221",
            "hdfc bank a/c xx3221", "hdfcbk"
        ],
        "is_active": True,
    },
    {
        "bank_name": "State Bank of India",
        "ifsc_prefix": "SBIN",
        "account_number_masked": "xx3724",
        "account_type": "savings",
        "sender_aliases": [
            "JK-SBYONO-S", "AD-SBIPSG-T", "VA-SBIPSG-T", "AX-SBIPSG-T",
            "AD-CBSSBI-S", "VM-SBIPSG-T", "SBIPSG", "SBYONO"
        ],
        "receiver_aliases": [
            "sbi", "state bank", "sbi a/c", "a/c xx3724",
            "sbi account", "yono sbi"
        ],
        "is_active": True,
    },
    {
        "bank_name": "SBI Credit Card",
        "ifsc_prefix": "SBIN",
        "account_number_masked": "xx8707",
        "account_type": "credit",
        "sender_aliases": [
            "AD-SBICRD-S", "VM-SBICRD-S", "VM-MYSBIC-S", "VD-MYSBIC-S",
            "SBICRD", "MYSBIC"
        ],
        "receiver_aliases": [
            "sbi card", "sbi credit card", "sbi cards and payment",
            "sbi cards and paymen", "card ending 8707", "card xx8707"
        ],
        "is_active": True,
    },
    {
        "bank_name": "SBI Savings (Secondary)",
        "ifsc_prefix": "SBIN",
        "account_number_masked": "xx9859",
        "account_type": "savings",
        "sender_aliases": [
            "AD-CBSSBI-S"
        ],
        "receiver_aliases": [
            "a/c xxxxx797859", "sbi savings"
        ],
        "is_active": True,
    },
]
