"""
scripts/fyi_backfill_orphaned_routes.py

One-time backfill: finds all COMPLETED fyi_agent signal_routes that have no
corresponding information_items record (caused by old agent version not writing them),
re-classifies each signal using the CURRENT fyi_agent logic, and inserts the missing record.

Usage:
    .venv/bin/python3 scripts/fyi_backfill_orphaned_routes.py           # live run
    .venv/bin/python3 scripts/fyi_backfill_orphaned_routes.py --dry-run # preview only
"""

import sys
import os
import json
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase import create_client, Client, ClientOptions
from configs.settings import settings
from src.agents.fyi.fyi_agent import FyiAgent
from loguru import logger

DRY_RUN = "--dry-run" in sys.argv
BATCH_SIZE = 50

def get_supabase_client() -> Client:
    url = settings.supabase_url
    key = settings.supabase_key
    return create_client(url, key, options=ClientOptions(schema="jarvis_insights_schemav1"))


def fetch_orphaned_routes(client: Client) -> list[dict]:
    """Find all COMPLETED fyi_agent routes with no information_items record."""
    logger.info("Fetching all COMPLETED fyi_agent routes...")
    all_routes = []
    offset = 0
    page_size = 1000

    while True:
        res = (
            client.table("signal_routes")
            .select("id, understood_signal_id")
            .eq("agent_name", "fyi_agent")
            .eq("route_status", "COMPLETED")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = res.data or []
        all_routes.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size

    logger.info(f"Total COMPLETED fyi_agent routes: {len(all_routes)}")

    # Find which have no information_items
    route_ids = [r["id"] for r in all_routes]
    existing_items = set()
    for i in range(0, len(route_ids), BATCH_SIZE):
        chunk = route_ids[i:i + BATCH_SIZE]
        res = (
            client.table("information_items")
            .select("route_id")
            .in_("route_id", chunk)
            .execute()
        )
        for row in (res.data or []):
            existing_items.add(row["route_id"])

    orphaned = [r for r in all_routes if r["id"] not in existing_items]
    logger.info(f"Orphaned routes (no information_items): {len(orphaned)}")
    return orphaned


def fetch_signal_data(client: Client, us_id: str) -> tuple[dict, dict]:
    """Fetch understood_signal and qualified_signal for a given understood_signal_id."""
    us_res = (
        client.table("understood_signals")
        .select("id, summary, contract_json, qualified_signal_id")
        .eq("id", us_id)
        .single()
        .execute()
    )
    us = us_res.data or {}

    qs = {}
    if us.get("qualified_signal_id"):
        qs_res = (
            client.table("qualified_signals")
            .select("id, message, sender, source, timestamp")
            .eq("id", us["qualified_signal_id"])
            .single()
            .execute()
        )
        qs = qs_res.data or {}

    return us, qs


def run_backfill():
    client = get_supabase_client()
    agent = FyiAgent()

    orphaned = fetch_orphaned_routes(client)
    if not orphaned:
        logger.success("No orphaned routes found. Nothing to backfill.")
        return

    if DRY_RUN:
        logger.warning(f"DRY RUN — would backfill {len(orphaned)} routes. No writes will happen.")

    success_count = 0
    skip_count = 0
    error_count = 0

    for i, route in enumerate(orphaned):
        route_id = route["id"]
        us_id = route.get("understood_signal_id")

        logger.info(f"[{i+1}/{len(orphaned)}] Backfilling route {route_id[:8]}...")

        try:
            if not us_id:
                logger.warning(f"  Route {route_id[:8]} has no understood_signal_id — skipping.")
                skip_count += 1
                continue

            us, qs = fetch_signal_data(client, us_id)
            raw_message = qs.get("message") or us.get("summary") or ""
            if not raw_message:
                logger.warning(f"  Route {route_id[:8]} has no message content — skipping.")
                skip_count += 1
                continue

            contract = us.get("contract_json") or {}
            sender = qs.get("sender") or "UNKNOWN"
            orig_timestamp = qs.get("timestamp") or datetime.now(timezone.utc).isoformat()

            # Re-classify using current FYI agent logic
            decision = agent._classify_and_route(raw_message, contract)

            evt_dt = decision.get("event_datetime")
            if evt_dt and isinstance(evt_dt, str) and evt_dt.strip().lower() in ("null", "none", ""):
                evt_dt = None

            info_item = {
                "route_id": route_id,
                "processing_path": decision["processing_path"],
                "category": decision["category"],
                "title": decision["title"],
                "summary": decision["summary"],
                "raw_payload": {
                    "sender": sender,
                    "timestamp": orig_timestamp,
                    "raw_message": raw_message,
                    "contract": contract,
                    "backfill": True,  # audit flag: written by backfill script
                    "backfill_at": datetime.now(timezone.utc).isoformat(),
                },
                "event_datetime": evt_dt,
                "timeline_group_id": decision.get("timeline_group_id"),
                "importance_level": decision["importance_level"],
            }

            logger.info(
                f"  [{decision['processing_path']}] {decision['category']} / "
                f"{decision['importance_level']} — {decision['title']!r}"
            )
            logger.debug(f"  Message: {raw_message[:80]}")

            if not DRY_RUN:
                client.table("information_items").insert(info_item).execute()

            success_count += 1

        except Exception as e:
            logger.error(f"  Failed to backfill route {route_id[:8]}: {e}")
            error_count += 1

    logger.info("=" * 60)
    logger.info("BACKFILL COMPLETE")
    logger.info(f"  Processed : {len(orphaned)}")
    logger.info(f"  Written   : {success_count}{' (DRY RUN — not actually written)' if DRY_RUN else ''}")
    logger.info(f"  Skipped   : {skip_count}")
    logger.info(f"  Errors    : {error_count}")


if __name__ == "__main__":
    run_backfill()
