# services/financial_classifier.py
# Financial Agent V2 — Revised

from loguru import logger
from services.rules_engine import RulesEngine
from configs.constants import TaskType
from intelligence.routing.router import IntelligenceRouter
import json


class FinancialClassifier:
    """
    Classifies financial transactions into typed spend categories.

    Resolution order:
      1. Pre-seeded merchant registry (MERCHANT_SEED) — ships with 24 merchants
      2. Heuristic keyword checks (fish, mutton, vegetables)
      3. RulesEngine (user overrides + dynamic merchant map)
      4. LLM fallback (cached)
    """

    # -------------------------------------------------------------------------
    # Category taxonomy (Financial Agent V2)
    # -------------------------------------------------------------------------
    ALLOWED_CATEGORIES = {
        # Lifestyle spend categories
        "FOOD_DINING",
        "GROCERIES",
        "TRANSPORT",
        "TRAVEL",
        "ENTERTAINMENT",
        "MEDICAL",
        "SHOPPING",
        "UTILITIES",
        "EDUCATION",
        "FAMILY",
        # Financial obligation categories
        "INSURANCE",
        "INVESTMENT",
        "BILL_PAYMENT",
        # Niche personal categories
        "FISH",
        "MUTTON",
        "VEGETABLES",
        "FUEL",
        # Income & special fact types (used by aggregation layer, not spend)
        "INCOME_SALARY",
        "INCOME_UNCLASSIFIED",
        "REFUND_EVENT",
        "INTERNAL_TRANSFER",
        # Fallback
        "OTHER",
    }

    # Categories excluded from Lifestyle Spend computation
    NON_LIFESTYLE_CATEGORIES = {"INVESTMENT", "INSURANCE", "BILL_PAYMENT", "INTERNAL_TRANSFER"}

    # -------------------------------------------------------------------------
    # Pre-seeded merchant registry (V2 — shipped with implementation)
    # Maps lowercase alias fragments → canonical category.
    # Resolution: any alias is checked as a substring of the lowercased text.
    # -------------------------------------------------------------------------
    MERCHANT_SEED: dict[str, str] = {
        # FOOD_DINING
        "zomato":               "FOOD_DINING",
        "zmt":                  "FOOD_DINING",
        "swiggy":               "FOOD_DINING",
        # GROCERIES
        "bigbasket":            "GROCERIES",
        "bb online":            "GROCERIES",
        "zepto":                "GROCERIES",
        "blinkit":              "GROCERIES",
        "grofers":              "GROCERIES",
        # MEDICAL
        "apollo pharmacy":      "MEDICAL",
        "aplphr":               "MEDICAL",
        "apollopharmacy":       "MEDICAL",
        "medplus":              "MEDICAL",
        # UTILITIES
        "airtel":               "UTILITIES",
        "airtelin":             "UTILITIES",
        "jio":                  "UTILITIES",
        "jiomoney":             "UTILITIES",
        "tneb":                 "UTILITIES",
        "tangedco":             "UTILITIES",
        "tnebl":                "UTILITIES",
        # ENTERTAINMENT
        "netflix":              "ENTERTAINMENT",
        "spotify":              "ENTERTAINMENT",
        "amazon prime":         "ENTERTAINMENT",
        "prime video":          "ENTERTAINMENT",
        "hotstar":              "ENTERTAINMENT",
        "disney hotstar":       "ENTERTAINMENT",
        # SHOPPING
        "amazon seller":        "SHOPPING",
        "flipkart":             "SHOPPING",
        # TRANSPORT
        "ola cabs":             "TRANSPORT",
        "uber india":           "TRANSPORT",
        "rapido":               "TRANSPORT",
        # TRAVEL
        "irctc":                "TRAVEL",
        "makemytrip":           "TRAVEL",
        "mmt":                  "TRAVEL",
        # INSURANCE
        "coverfox":             "INSURANCE",
        "licind":               "INSURANCE",
        "lic of india":         "INSURANCE",
        # BILL_PAYMENT
        "sbi card":             "BILL_PAYMENT",
        "sbicrd":               "BILL_PAYMENT",
        "sbi cards":            "BILL_PAYMENT",
        "hdfc card":            "BILL_PAYMENT",
        "hdfcbk card":          "BILL_PAYMENT",
        # INVESTMENT (common SIP / brokerage patterns)
        "zerodha":              "INVESTMENT",
        "groww":                "INVESTMENT",
        "coin by zerodha":      "INVESTMENT",
        "paytm money":          "INVESTMENT",
        "mirae asset":          "INVESTMENT",
        "axis mutual":          "INVESTMENT",
        "sbi mutual":           "INVESTMENT",
        "hdfc mutual":          "INVESTMENT",
        "icici pru":            "INVESTMENT",
        "franklin templeton":   "INVESTMENT",
        "navi mutual":          "INVESTMENT",
    }

    @classmethod
    def classify_transaction(
        cls,
        title: str,
        merchant: str = None,
        vpa: str = None,
        paid_to: str = None,
        paid_from: str = None,
    ) -> tuple[str, float]:
        """
        Classifies a transaction into one of the allowed categories.
        Returns a tuple of (category, confidence).

        Resolution order:
          1. Merchant seed registry (pre-seeded, substring match)
          2. Heuristic keyword checks (fish / mutton / vegetables)
          3. RulesEngine (user overrides + dynamic merchant map)
          4. LLM fallback (cached)
        """
        m_name = (merchant or paid_to or "").strip()
        v_handle = (vpa or "").strip()
        t_title = (title or "").strip()
        search_text = f"{t_title} {m_name} {v_handle}".lower()

        # ── Step 1: Pre-seeded merchant registry ─────────────────────────────
        for alias, category in cls.MERCHANT_SEED.items():
            if alias in search_text:
                logger.info(f"MerchantSeed match: '{alias}' → '{category}' (text: '{search_text[:60]}')")
                return category, 1.0

        # ── Step 2: Heuristic keyword checks ─────────────────────────────────
        t_lower = search_text
        if "fish" in t_lower or "meen" in t_lower or "fresh catch" in t_lower:
            return "FISH", 1.0
        if "mutton" in t_lower or "goat" in t_lower or "fresh meat" in t_lower:
            return "MUTTON", 1.0
        if "vegetable" in t_lower or "greens" in t_lower:
            return "VEGETABLES", 1.0

        # ── Step 3: RulesEngine (dynamic rules + user overrides) ─────────────
        category = RulesEngine.categorize_transaction(m_name, v_handle, t_title)
        category_upper = category.upper()

        if category_upper in cls.ALLOWED_CATEGORIES and category_upper != "OTHER":
            logger.info(f"RulesEngine match: '{t_title}' → '{category_upper}'")
            return category_upper, 1.0

        # ── Step 4: LLM classification (cached) ──────────────────────────────
        import hashlib
        from storage.repositories.classification_cache_repository import ClassificationCacheRepository

        raw_str = f"tx_class:{t_title}:{m_name}:{v_handle}:{paid_from or ''}"
        cache_key = hashlib.sha256(raw_str.encode("utf-8")).hexdigest()

        cached = ClassificationCacheRepository.get(cache_key)
        if cached and "category" in cached and "confidence" in cached:
            logger.info(f"LLM cache HIT: '{t_title}' → '{cached['category']}'")
            return cached["category"], cached["confidence"]

        logger.info(f"LLM fallback: '{t_title}' (merchant: '{m_name}', VPA: '{v_handle}')")
        try:
            llm_cat = cls._llm_classify(t_title, m_name, v_handle, paid_from)
            if llm_cat in cls.ALLOWED_CATEGORIES:
                logger.info(f"LLM classified: '{t_title}' → '{llm_cat}'")
                ClassificationCacheRepository.set(cache_key, {"category": llm_cat, "confidence": 0.9})
                return llm_cat, 0.9
        except Exception as e:
            logger.error(f"LLM classification failed for '{t_title}': {e}")

        ClassificationCacheRepository.set(cache_key, {"category": "OTHER", "confidence": 0.5})
        return "OTHER", 0.5

    @classmethod
    def is_lifestyle_category(cls, category: str) -> bool:
        """Returns True if the category counts toward Lifestyle Spend."""
        return category not in cls.NON_LIFESTYLE_CATEGORIES and category in cls.ALLOWED_CATEGORIES

    @classmethod
    def _llm_classify(cls, title: str, merchant: str, vpa: str, paid_from: str) -> str:
        """Calls local LLM to classify a transaction into one of the allowed categories."""
        router = IntelligenceRouter()
        # Exclude internal system categories from LLM prompt — LLM should not guess these
        llm_categories = cls.ALLOWED_CATEGORIES - {
            "INTERNAL_TRANSFER", "INCOME_SALARY", "INCOME_UNCLASSIFIED", "REFUND_EVENT"
        }
        categories_list = ", ".join(sorted(llm_categories))

        prompt = f"""You are a financial transaction classifier for an Indian user.
Classify the following transaction into exactly one of these allowed categories:
{categories_list}

Transaction Details:
- Title/Description: {title}
- Merchant: {merchant}
- UPI VPA: {vpa}
- Source/Paid From: {paid_from}

Return ONLY the category name in uppercase. Do not return any other text, explanation, or markdown.
"""
        response = router.ask(prompt=prompt, task_type=TaskType.EMAIL)
        cleaned = response.strip().upper().replace('"', "").replace("'", "").replace("`", "")

        for word in cleaned.split():
            if word in cls.ALLOWED_CATEGORIES:
                return word

        return "OTHER"
