# services/financial_classifier.py

from loguru import logger
from services.rules_engine import RulesEngine
from configs.constants import TaskType
from intelligence.routing.router import IntelligenceRouter
import json


class FinancialClassifier:
    # Standard allowed categories for the outflow analysis
    ALLOWED_CATEGORIES = {
        "GROCERY",
        "FISH",
        "MUTTON",
        "VEGETABLES",
        "FUEL",
        "MEDICAL",
        "SHOPPING",
        "UTILITIES",
        "INSURANCE",
        "EDUCATION",
        "TRAVEL",
        "ENTERTAINMENT",
        "FAMILY",
        "OTHER",
        "INTERNAL_TRANSFER"
    }

    @classmethod
    def classify_transaction(
        cls,
        title: str,
        merchant: str = None,
        vpa: str = None,
        paid_to: str = None,
        paid_from: str = None
    ) -> tuple[str, float]:
        """
        Classifies a transaction into one of the allowed categories.
        Returns a tuple of (category, confidence).
        """
        # Resolve merchant name and VPA
        m_name = merchant or paid_to or ""
        v_handle = vpa or ""
        t_title = title or ""

        # Level 3 & Level 1: RulesEngine handles User Overrides and Merchant Mapping
        category = RulesEngine.categorize_transaction(m_name, v_handle, t_title)
        category_upper = category.upper()

        if category_upper in cls.ALLOWED_CATEGORIES and category_upper != "OTHER":
            logger.info(f"RulesEngine match: '{t_title}' mapped to '{category_upper}'")
            return category_upper, 1.0

        # Heuristic checks for special categories
        t_lower = t_title.lower()
        if "fish" in t_lower or "meen" in t_lower or "fresh catch" in t_lower:
            return "FISH", 1.0
        if "mutton" in t_lower or "meat" in t_lower or "goat" in t_lower or "fresh meat" in t_lower:
            return "MUTTON", 1.0
        if "vegetable" in t_lower or "veg" in t_lower or "greens" in t_lower:
            return "VEGETABLES", 1.0

        # Level 2: LLM Classification Fallback
        import hashlib
        from storage.repositories.classification_cache_repository import ClassificationCacheRepository

        raw_str = f"tx_class:{t_title}:{m_name}:{v_handle}:{paid_from or ''}"
        cache_key = hashlib.sha256(raw_str.encode("utf-8")).hexdigest()

        cached = ClassificationCacheRepository.get(cache_key)
        if cached and "category" in cached and "confidence" in cached:
            logger.info(f"Financial Classifier Cache HIT: '{t_title}' mapped to '{cached['category']}'")
            return cached["category"], cached["confidence"]

        logger.info(f"Fallback to LLM for transaction: '{t_title}' (merchant: '{m_name}', VPA: '{v_handle}')")
        try:
            llm_cat = cls._llm_classify(t_title, m_name, v_handle, paid_from)
            if llm_cat in cls.ALLOWED_CATEGORIES:
                logger.info(f"LLM successfully classified transaction to '{llm_cat}'")
                ClassificationCacheRepository.set(cache_key, {"category": llm_cat, "confidence": 0.9})
                return llm_cat, 0.9
        except Exception as e:
            logger.error(f"LLM classification failed for transaction '{t_title}': {e}")

        # Cache the fallback "OTHER" result as well to prevent repeatedly calling LLM for failures
        ClassificationCacheRepository.set(cache_key, {"category": "OTHER", "confidence": 0.5})
        return "OTHER", 0.5

    @classmethod
    def _llm_classify(cls, title: str, merchant: str, vpa: str, paid_from: str) -> str:
        """
        Calls local LLM to classify raw details into one of the allowed categories.
        """
        router = IntelligenceRouter()
        categories_list = ", ".join(cls.ALLOWED_CATEGORIES)
        
        prompt = f"""
You are a financial transaction classifier.
Classify the following transaction into exactly one of these allowed categories:
{categories_list}

Transaction Details:
- Title/Description: {title}
- Merchant: {merchant}
- UPI VPA: {vpa}
- Source/Paid From: {paid_from}

Return ONLY the category name in uppercase. Do not return any other text, explanation, or markdown.
"""
        response = router.ask(
            prompt=prompt,
            task_type=TaskType.EMAIL,  # routes to local LLM locally
        )
        cleaned = response.strip().upper().replace('"', '').replace("'", "").replace("`", "")
        
        # Search for first matched category in the clean output words
        for word in cleaned.split():
            if word in cls.ALLOWED_CATEGORIES:
                return word

        return "OTHER"
