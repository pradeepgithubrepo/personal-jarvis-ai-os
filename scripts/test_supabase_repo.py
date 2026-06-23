# scripts/test_supabase_repo.py

import os
import sys
import uuid
from datetime import datetime
from loguru import logger

# Add root folder to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.supabase_repo import SupabaseRepo, supabase

def test_repo():
    logger.info("Starting Supabase Repo Integration test...")

    # Unique test IDs
    test_sig_id = uuid.uuid4()
    test_todo_id = uuid.uuid4()
    test_event_id = uuid.uuid4()
    test_fyi_id = uuid.uuid4()
    test_fact_id = uuid.uuid4()
    test_action_id = uuid.uuid4()
    pref_key = f"test_pref_{uuid.uuid4().hex[:6]}"

    try:
        # 1. save_signal
        logger.info("Testing save_signal...")
        ok = SupabaseRepo.save_signal(
            signal_id=test_sig_id,
            source="whatsapp",
            sender="Pradeep",
            message="Validating signal save",
            signal_timestamp=datetime.utcnow(),
            created_at=datetime.utcnow(),
            raw_signal_id="1234",
            metadata={"test": True}
        )
        assert ok, "save_signal failed"

        # 2. create_todo
        logger.info("Testing create_todo...")
        ok = SupabaseRepo.create_todo(
            todo_id=test_todo_id,
            title="Sanity check todo",
            description="Testing API operations",
            priority="high",
            status="OPEN",
            due_date=datetime.utcnow(),
            source_signal_id=test_sig_id
        )
        assert ok, "create_todo failed"

        # 3. update_todo_status
        logger.info("Testing update_todo_status...")
        ok = SupabaseRepo.update_todo_status(test_todo_id, "COMPLETED")
        assert ok, "update_todo_status failed"

        # 4. create_financial_event
        logger.info("Testing create_financial_event...")
        ok = SupabaseRepo.create_financial_event(
            event_id=test_event_id,
            merchant="Zepto",
            amount=350.0,
            currency="INR",
            category="Grocery",
            status="OPEN",
            event_timestamp=datetime.utcnow(),
            source_signal_id=test_sig_id
        )
        assert ok, "create_financial_event failed"

        # 5. reclassify_financial_event
        logger.info("Testing reclassify_financial_event...")
        ok = SupabaseRepo.reclassify_financial_event(test_event_id, "Food")
        assert ok, "reclassify_financial_event failed"

        # 6. create_fyi_event
        logger.info("Testing create_fyi_event...")
        ok = SupabaseRepo.create_fyi_event(
            event_id=test_fyi_id,
            title="School picnic circular",
            summary="Picnic details",
            category="school_circular",
            read_flag=False,
            source_signal_id=test_sig_id
        )
        assert ok, "create_fyi_event failed"

        # 7. mark_fyi_read
        logger.info("Testing mark_fyi_read...")
        ok = SupabaseRepo.mark_fyi_read(test_fyi_id, True)
        assert ok, "mark_fyi_read failed"

        # 8. store_fact
        logger.info("Testing store_fact...")
        ok = SupabaseRepo.store_fact(
            fact_id=test_fact_id,
            entity="Charan",
            fact="Picnic on July 5",
            confidence=0.9,
            source_signal_id=test_sig_id
        )
        assert ok, "store_fact failed"

        # 9. store_preference
        logger.info("Testing store_preference...")
        ok = SupabaseRepo.store_preference(pref_key, "active")
        assert ok, "store_preference failed"

        # 10. store_user_action
        logger.info("Testing store_user_action...")
        ok = SupabaseRepo.store_user_action(
            action_id=test_action_id,
            entity_type="Todo",
            entity_id=str(test_todo_id),
            action="Completed Todo",
            metadata={"source": "test_script"}
        )
        assert ok, "store_user_action failed"

        logger.success("All CRUD operations executed successfully!")

        # 11. Read back and verify values
        logger.info("Reading back values to verify correctness...")
        todo_data = supabase.table("todos").select("*").eq("todo_id", str(test_todo_id)).execute().data
        assert todo_data and todo_data[0]["status"] == "COMPLETED", f"Todo verify failed: {todo_data}"

        pref_data = supabase.table("user_preferences").select("*").eq("preference_key", pref_key).execute().data
        assert pref_data and pref_data[0]["preference_value"] == "active", f"Preference verify failed: {pref_data}"

        logger.success("Read back and verification successful! Data matches exactly.")

        # Cleanup test records
        logger.info("Cleaning up test records from database...")
        supabase.table("user_actions").delete().eq("action_id", str(test_action_id)).execute()
        supabase.table("user_preferences").delete().eq("preference_key", pref_key).execute()
        supabase.table("facts").delete().eq("fact_id", str(test_fact_id)).execute()
        supabase.table("fyi_events").delete().eq("fyi_event_id", str(test_fyi_id)).execute()
        supabase.table("financial_events").delete().eq("financial_event_id", str(test_event_id)).execute()
        supabase.table("todos").delete().eq("todo_id", str(test_todo_id)).execute()
        supabase.table("signals").delete().eq("signal_id", str(test_sig_id)).execute()
        logger.success("Cleanup completed successfully.")
        logger.success("SUPABASE REPOSITORY INTEGRATION TEST PASSED SUCCESSFULLY!")

    except Exception as e:
        logger.exception(f"Integration test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_repo()
