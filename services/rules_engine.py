# services/rules_engine.py

import os
import json
import re
from loguru import logger


class RulesEngine:
    """
    Jarvis Intelligence Configuration Rules Engine
    Loads configuration JSON files dynamically and applies rules.
    """

    _rules = {}
    _overrides = {}
    
    # Absolute paths to configuration files
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    RULES_FILE = os.path.join(PROJECT_ROOT, "config", "jarvis_rules.json")
    OVERRIDES_FILE = os.path.join(PROJECT_ROOT, "config", "user_overrides.json")

    @classmethod
    def load_rules(cls):
        """Loads or reloads configuration files from disk into memory."""
        # 1. Load default jarvis rules
        if os.path.exists(cls.RULES_FILE):
            try:
                with open(cls.RULES_FILE, "r") as f:
                    cls._rules = json.load(f) or {}
                logger.info(f"Successfully loaded default rules from {cls.RULES_FILE}")
            except Exception as e:
                logger.error(f"Error loading jarvis rules config: {e}")
                cls._rules = {}
        else:
            logger.warning(f"Jarvis rules file not found at {cls.RULES_FILE}. Using empty defaults.")
            cls._rules = {}

        # 2. Load user overrides
        if os.path.exists(cls.OVERRIDES_FILE):
            try:
                with open(cls.OVERRIDES_FILE, "r") as f:
                    cls._overrides = json.load(f) or {}
                logger.info(f"Successfully loaded user overrides from {cls.OVERRIDES_FILE}")
            except Exception as e:
                logger.error(f"Error loading user overrides config: {e}")
                cls._overrides = {}
        else:
            logger.warning(f"User overrides file not found at {cls.OVERRIDES_FILE}. Using empty overrides.")
            cls._overrides = {}

    @classmethod
    def reload(cls):
        """Reloads all rules from disk."""
        cls.load_rules()

    @classmethod
    def should_ignore_signal(cls, summary: str, raw_json_str: str = None) -> bool:
        """
        Evaluates whether a signal matches any ignore topics or financial exclusions.
        Returns True if the signal should be categorized as IGNORE, False otherwise.
        """
        if not cls._rules:
            cls.load_rules()

        summary_lower = (summary or "").lower()
        
        # 1. Check ignore_topics (Section 1)
        ignore_topics = cls._rules.get("ignore_topics", [])
        for topic in ignore_topics:
            if topic.lower() in summary_lower:
                logger.debug(f"Signal ignored due to topic match: '{topic}' in summary '{summary}'")
                return True

        # 2. Check financial exclusions (Section 6)
        financial_ignore = cls._rules.get("financial_ignore", [])
        for term in financial_ignore:
            term_lower = term.lower()
            if term_lower in summary_lower:
                logger.debug(f"Signal ignored due to financial exclusion match: '{term}' in summary '{summary}'")
                return True

        # 3. Parse raw_json if provided
        if raw_json_str:
            try:
                details = json.loads(raw_json_str) or {}
                # Check raw_json values for any ignore keywords
                for val in details.values():
                    if isinstance(val, str):
                        val_lower = val.lower()
                        for topic in ignore_topics:
                            if topic.lower() in val_lower:
                                logger.debug(f"Signal ignored due to topic match in json: '{topic}'")
                                return True
                        for term in financial_ignore:
                            if term.lower() in val_lower:
                                logger.debug(f"Signal ignored due to financial exclusion match in json: '{term}'")
                                return True
            except Exception:
                pass

        return False

    @classmethod
    def categorize_transaction(cls, merchant: str, vpa: str, summary: str) -> str:
        """
        Determines the category for a transaction based on overrides, merchant names, UPI VPA names,
        custom user keyword patterns, and fallbacks.
        """
        if not cls._rules:
            cls.load_rules()

        # Normalize inputs for exact key matching (stripped and lowercased)
        m_norm = (merchant or "").strip().lower()
        v_norm = (vpa or "").strip().lower()
        s_norm = (summary or "").strip().lower()

        # Step 1: Check User Overrides (Section 5)
        overrides = cls._overrides.get("overrides", {})
        
        # Check by merchant name first in overrides
        if m_norm and m_norm in overrides:
            logger.debug(f"Override category matched for merchant '{merchant}': {overrides[m_norm]}")
            return overrides[m_norm].upper()
            
        # Check by VPA name in overrides
        if v_norm and v_norm in overrides:
            logger.debug(f"Override category matched for VPA '{vpa}': {overrides[v_norm]}")
            return overrides[v_norm].upper()

        # Check if override key is present in merchant or summary
        for key, cat in overrides.items():
            key_lower = key.lower()
            if (m_norm and key_lower in m_norm) or (key_lower in s_norm):
                logger.debug(f"Override category matched for keyword '{key}': {cat}")
                return cat.upper()

        # Step 2: Check Merchant Categories (Section 2)
        merchant_cats = cls._rules.get("merchant_categories", {})
        if m_norm and m_norm in merchant_cats:
            logger.debug(f"Merchant category matched for '{merchant}': {merchant_cats[m_norm]}")
            return merchant_cats[m_norm].upper()

        # Also support partial merchant matches if the merchant starts with or matches a pattern, or is in summary
        for key, cat in merchant_cats.items():
            key_lower = key.lower()
            if (m_norm and key_lower in m_norm) or (key_lower in s_norm):
                logger.debug(f"Merchant category matched for keyword '{key}' in merchant/summary: {cat}")
                return cat.upper()

        # Step 3: Check UPI patterns (Section 3)
        upi_patterns = cls._rules.get("upi_patterns", {})
        if v_norm:
            # Direct match
            if v_norm in upi_patterns:
                logger.debug(f"UPI pattern category matched for VPA '{vpa}': {upi_patterns[v_norm]}")
                return upi_patterns[v_norm].upper()
            # Partial match
            for key, cat in upi_patterns.items():
                if key.lower() in v_norm:
                    logger.debug(f"Partial UPI pattern category matched for VPA '{vpa}' against '{key}': {cat}")
                    return cat.upper()

        # Also check if any UPI pattern key appears in the summary
        for key, cat in upi_patterns.items():
            if key.lower() in s_norm:
                logger.debug(f"UPI pattern category matched for summary containing '{key}': {cat}")
                return cat.upper()

        # Step 4: Check Custom categories (Section 4)
        custom_cats = cls._rules.get("custom_categories", {})
        for cat_name, keywords in custom_cats.items():
            for kw in keywords:
                kw_lower = kw.lower()
                # Check for presence in merchant name or summary
                if (m_norm and kw_lower in m_norm) or (kw_lower in s_norm):
                    logger.debug(f"Custom user category matched: '{kw_lower}' maps to '{cat_name}'")
                    return cat_name.upper()

        # Step 5: Fallback
        return "OTHER"


# Initial loading of rules
RulesEngine.load_rules()
