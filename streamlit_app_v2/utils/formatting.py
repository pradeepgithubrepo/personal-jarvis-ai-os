# streamlit_app_v2/utils/formatting.py

from datetime import datetime

def format_currency(val):
    """Formats values in INR ₹ currency."""
    if val is None:
        return "₹0.00"
    try:
        val = float(val)
        return f"₹{val:,.2f}"
    except (ValueError, TypeError):
        return str(val)

def format_timestamp(ts_str):
    """Formats ISO/Database timestamps into human-readable format."""
    if not ts_str:
        return "N/A"
    try:
        # standardise timezone
        ts_str = ts_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts_str)
        return dt.strftime("%b %d, %Y %I:%M %p")
    except Exception:
        # Fallback split
        try:
            parts = ts_str.split("T")
            date_part = parts[0]
            time_part = parts[1].split(".")[0] if len(parts) > 1 else ""
            return f"{date_part} {time_part}"
        except Exception:
            return str(ts_str)

def clean_brief_display(content):
    """Formats markdown structures inside briefs cleanly."""
    if not content:
        return "No content available."
    return content.strip()
