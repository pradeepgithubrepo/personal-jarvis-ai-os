# services/context_provider.py

import os
import json
from loguru import logger


class ContextProvider:
    """
    Jarvis Context Provider
    Loads user_context.json dynamically and constructs the prompt context.
    """

    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    CONTEXT_FILE = os.path.join(PROJECT_ROOT, "config", "user_context.json")
    _cached_context = None
    _cached_mtime = 0

    @classmethod
    def load_context(cls) -> dict:
        """Loads user_context.json from disk, with caching based on file modification time."""
        if not os.path.exists(cls.CONTEXT_FILE):
            logger.warning(f"User context file not found at {cls.CONTEXT_FILE}")
            return {}

        try:
            mtime = os.path.getmtime(cls.CONTEXT_FILE)
            if cls._cached_context is not None and mtime == cls._cached_mtime:
                return cls._cached_context

            with open(cls.CONTEXT_FILE, "r") as f:
                cls._cached_context = json.load(f)
                cls._cached_mtime = mtime
            logger.info(f"Loaded user context from {cls.CONTEXT_FILE}")
            return cls._cached_context
        except Exception as e:
            logger.error(f"Error loading user context JSON: {e}")
            return {}

    @classmethod
    def get_context_prompt(cls) -> str:
        """
        Dynamically constructs the context prompt from the user_context.json file.
        Returns a formatted string to be prepended to LLM prompts.
        """
        context = cls.load_context()
        if not context:
            return ""

        lines = ["Jarvis User Context", ""]
        
        # User details
        user_name = context.get("user", {}).get("name")
        if user_name:
            lines.append(f"User: {user_name}")
            lines.append("")

        # Family details
        family = context.get("family", {})
        spouse = family.get("spouse")
        if spouse:
            lines.append("Spouse:")
            lines.append(f"- {spouse}")
            lines.append("")

        children = family.get("children", [])
        if children:
            lines.append("Children:")
            for child in children:
                lines.append(f"- {child}")
            lines.append("")

        # Preferences & Priorities mapping
        prefs = context.get("preferences", {})
        priorities = context.get("priorities", {})
        
        if prefs.get("family_messages_are_important") or priorities.get("family") == "HIGH":
            lines.append("Family related messages are important.")
            lines.append("")
            
        if priorities.get("school") == "HIGH" or prefs.get("school_messages_are_actionable"):
            # Construct based on children
            if children:
                lines.append("School related messages involving the children are high priority.")
            else:
                lines.append("School related messages are high priority.")
            lines.append("")

        if prefs.get("financial_alerts_are_important") or priorities.get("finance") == "HIGH":
            lines.append("Financial alerts and reminders are high priority.")
            lines.append("")

        ignore_topics = context.get("ignore_topics", [])
        if "badminton" in ignore_topics:
            lines.append("Badminton related information should be ignored unless explicitly actionable.")
            lines.append("")

        # Return joined with exactly one trailing newline
        return "\n".join(lines).strip() + "\n\n"
