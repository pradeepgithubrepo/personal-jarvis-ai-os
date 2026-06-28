# storage/seeds/merchant_seed.py
"""
Pre-seeded canonical merchant registry.
Covers the most common Indian consumer merchants across all expense categories.
The Financial Agent resolves raw merchant strings from SUA contracts against these entries.
"""

MERCHANT_SEED = [
    # ── FOOD & DINING ─────────────────────────────────────────────────────────
    {
        "canonical_name": "Zomato",
        "category": "FOOD_DINING",
        "aliases": ["zomato", "zomato india", "zomato india pvt", "zmt", "zomato.com"],
        "is_trusted": True,
    },
    {
        "canonical_name": "Swiggy",
        "category": "FOOD_DINING",
        "aliases": ["swiggy", "swiggy order", "bundl technologies", "swiggy.in"],
        "is_trusted": True,
    },

    # ── GROCERIES ─────────────────────────────────────────────────────────────
    {
        "canonical_name": "BigBasket",
        "category": "GROCERIES",
        "aliases": ["bigbasket", "bb online", "innovative retail", "bigbasket.com"],
        "is_trusted": True,
    },
    {
        "canonical_name": "Zepto",
        "category": "GROCERIES",
        "aliases": ["zepto", "zepto app", "kiranakart"],
        "is_trusted": True,
    },
    {
        "canonical_name": "Blinkit",
        "category": "GROCERIES",
        "aliases": ["blinkit", "grofers", "grofers india", "blinkit.com"],
        "is_trusted": True,
    },
    {
        "canonical_name": "DMart",
        "category": "GROCERIES",
        "aliases": ["dmart", "d-mart", "avenue supermarts", "dmart ready"],
        "is_trusted": True,
    },

    # ── MEDICAL ───────────────────────────────────────────────────────────────
    {
        "canonical_name": "Apollo Pharmacy",
        "category": "MEDICAL",
        "aliases": ["apollo pharmacy", "aplphr", "apollopharmacy", "apollo pharmacie", "apollo health"],
        "is_trusted": True,
    },
    {
        "canonical_name": "MedPlus",
        "category": "MEDICAL",
        "aliases": ["medplus", "medplus pharmacy", "medplus health"],
        "is_trusted": True,
    },
    {
        "canonical_name": "Practo",
        "category": "MEDICAL",
        "aliases": ["practo", "practo.com"],
        "is_trusted": True,
    },

    # ── UTILITIES ─────────────────────────────────────────────────────────────
    {
        "canonical_name": "Airtel",
        "category": "UTILITIES",
        "aliases": ["airtel", "airtelin", "airtel mobile", "bharti airtel", "airtelnet"],
        "is_trusted": True,
    },
    {
        "canonical_name": "Jio",
        "category": "UTILITIES",
        "aliases": ["jio", "reliance jio", "jiomoney", "jio recharge"],
        "is_trusted": True,
    },
    {
        "canonical_name": "TNEB",
        "category": "UTILITIES",
        "aliases": ["tneb", "tangedco", "tnebl", "tneb ltd", "tamil nadu electricity"],
        "is_trusted": True,
    },
    {
        "canonical_name": "BSNL",
        "category": "UTILITIES",
        "aliases": ["bsnl", "bharat sanchar"],
        "is_trusted": True,
    },

    # ── ENTERTAINMENT ─────────────────────────────────────────────────────────
    {
        "canonical_name": "Netflix",
        "category": "ENTERTAINMENT",
        "aliases": ["netflix", "netflix.com", "netflix india"],
        "is_trusted": True,
    },
    {
        "canonical_name": "Spotify",
        "category": "ENTERTAINMENT",
        "aliases": ["spotify", "spotify india", "spotify ab"],
        "is_trusted": True,
    },
    {
        "canonical_name": "Amazon Prime",
        "category": "ENTERTAINMENT",
        "aliases": ["amazon prime", "prime video", "prime membership", "amazon prime video"],
        "is_trusted": True,
    },
    {
        "canonical_name": "Disney+ Hotstar",
        "category": "ENTERTAINMENT",
        "aliases": ["hotstar", "disney hotstar", "star india", "disney+"],
        "is_trusted": True,
    },

    # ── SHOPPING ──────────────────────────────────────────────────────────────
    {
        "canonical_name": "Amazon",
        "category": "SHOPPING",
        "aliases": ["amazon", "amazon seller", "amazon india", "amazon.in", "amazonpay"],
        "is_trusted": True,
    },
    {
        "canonical_name": "Flipkart",
        "category": "SHOPPING",
        "aliases": ["flipkart", "flipkart internet", "fk", "flipkart.com"],
        "is_trusted": True,
    },
    {
        "canonical_name": "Myntra",
        "category": "SHOPPING",
        "aliases": ["myntra", "myntra designs"],
        "is_trusted": True,
    },

    # ── TRANSPORT ─────────────────────────────────────────────────────────────
    {
        "canonical_name": "Ola",
        "category": "TRANSPORT",
        "aliases": ["ola", "ola cabs", "anisha mobi", "ola electric"],
        "is_trusted": True,
    },
    {
        "canonical_name": "Uber",
        "category": "TRANSPORT",
        "aliases": ["uber", "uber india", "uber technologies"],
        "is_trusted": True,
    },
    {
        "canonical_name": "Rapido",
        "category": "TRANSPORT",
        "aliases": ["rapido", "roppen transportation"],
        "is_trusted": True,
    },

    # ── TRAVEL ────────────────────────────────────────────────────────────────
    {
        "canonical_name": "IRCTC",
        "category": "TRAVEL",
        "aliases": ["irctc", "irctc ltd", "indian railways", "irctc ecatering"],
        "is_trusted": True,
    },
    {
        "canonical_name": "MakeMyTrip",
        "category": "TRAVEL",
        "aliases": ["makemytrip", "mmt", "make my trip", "makemytrip.com"],
        "is_trusted": True,
    },

    # ── INSURANCE ─────────────────────────────────────────────────────────────
    {
        "canonical_name": "LIC",
        "category": "INSURANCE",
        "aliases": ["lic", "licind", "lic of india", "life insurance corporation"],
        "is_trusted": True,
    },
    {
        "canonical_name": "Coverfox",
        "category": "INSURANCE",
        "aliases": ["coverfox", "coverfox insurance brokin", "coverfox insurance", "cvrfox"],
        "is_trusted": True,
    },
    {
        "canonical_name": "United India Insurance",
        "category": "INSURANCE",
        "aliases": ["united india", "uiicho", "united india insurance"],
        "is_trusted": True,
    },
    {
        "canonical_name": "HDFC Life",
        "category": "INSURANCE",
        "aliases": ["hdfc life", "hdfc standard life", "hdfclife"],
        "is_trusted": True,
    },
    {
        "canonical_name": "Policybazaar",
        "category": "INSURANCE",
        "aliases": ["policybazaar", "policy bazaar", "pb fintech"],
        "is_trusted": True,
    },
]
