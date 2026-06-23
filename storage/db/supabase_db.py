# storage/db/supabase_db.py

import sys
import psycopg2
from loguru import logger
from configs.settings import settings

# Exact Table Definitions for User SQL Editor Fallback
DDL_STATEMENTS = {
    "create_schema": "CREATE SCHEMA IF NOT EXISTS jarvis_insights_schema;",
    
    "signals": """
    CREATE TABLE IF NOT EXISTS jarvis_insights_schema.signals (
        signal_id UUID PRIMARY KEY,
        source TEXT,
        sender TEXT,
        message TEXT,
        signal_timestamp TIMESTAMP,
        created_at TIMESTAMP,
        raw_signal_id TEXT,
        metadata JSONB
    );
    """,
    
    "todos": """
    CREATE TABLE IF NOT EXISTS jarvis_insights_schema.todos (
        todo_id UUID PRIMARY KEY,
        title TEXT,
        description TEXT,
        priority TEXT,
        status TEXT CHECK (status IN ('OPEN', 'COMPLETED', 'SNOOZED', 'DISMISSED')),
        due_date TIMESTAMP,
        source_signal_id UUID,
        created_at TIMESTAMP,
        updated_at TIMESTAMP
    );
    """,
    
    "financial_events": """
    CREATE TABLE IF NOT EXISTS jarvis_insights_schema.financial_events (
        financial_event_id UUID PRIMARY KEY,
        merchant TEXT,
        amount NUMERIC,
        currency TEXT,
        category TEXT,
        status TEXT,
        event_timestamp TIMESTAMP,
        source_signal_id UUID,
        created_at TIMESTAMP,
        updated_at TIMESTAMP
    );
    """,
    
    "fyi_events": """
    CREATE TABLE IF NOT EXISTS jarvis_insights_schema.fyi_events (
        fyi_event_id UUID PRIMARY KEY,
        title TEXT,
        summary TEXT,
        category TEXT,
        read_flag BOOLEAN DEFAULT FALSE,
        source_signal_id UUID,
        created_at TIMESTAMP,
        updated_at TIMESTAMP
    );
    """,
    
    "facts": """
    CREATE TABLE IF NOT EXISTS jarvis_insights_schema.facts (
        fact_id UUID PRIMARY KEY,
        entity TEXT,
        fact TEXT,
        confidence NUMERIC,
        source_signal_id UUID,
        created_at TIMESTAMP
    );
    """,
    
    "merchant_mappings": """
    CREATE TABLE IF NOT EXISTS jarvis_insights_schema.merchant_mappings (
        mapping_id UUID PRIMARY KEY,
        merchant_name TEXT,
        category TEXT,
        confidence NUMERIC,
        created_at TIMESTAMP,
        updated_at TIMESTAMP
    );
    """,
    
    "user_preferences": """
    CREATE TABLE IF NOT EXISTS jarvis_insights_schema.user_preferences (
        preference_key TEXT PRIMARY KEY,
        preference_value TEXT,
        updated_at TIMESTAMP
    );
    """,
    
    "user_actions": """
    CREATE TABLE IF NOT EXISTS jarvis_insights_schema.user_actions (
        action_id UUID PRIMARY KEY,
        entity_type TEXT,
        entity_id TEXT,
        action TEXT,
        action_timestamp TIMESTAMP,
        metadata JSONB
    );
    """,

    "salary_cycles": """
    CREATE TABLE IF NOT EXISTS jarvis_insights_schema.salary_cycles (
        salary_cycle_id UUID PRIMARY KEY,
        salary_date TIMESTAMP,
        salary_amount NUMERIC,
        cycle_start TIMESTAMP,
        cycle_end TIMESTAMP,
        created_at TIMESTAMP
    );
    """,

    "monthly_financial_summary": """
    CREATE TABLE IF NOT EXISTS jarvis_insights_schema.monthly_financial_summary (
        summary_id UUID PRIMARY KEY,
        salary_cycle_id UUID,
        salary_amount NUMERIC,
        total_credit NUMERIC,
        total_debit NUMERIC,
        net_savings NUMERIC,
        created_at TIMESTAMP,
        updated_at TIMESTAMP
    );
    """,

    "monthly_category_spend": """
    CREATE TABLE IF NOT EXISTS jarvis_insights_schema.monthly_category_spend (
        entry_id UUID PRIMARY KEY,
        salary_cycle_id UUID,
        category_name TEXT,
        amount NUMERIC,
        transaction_count INTEGER,
        created_at TIMESTAMP
    );
    """,

    "monthly_category_trends": """
    CREATE TABLE IF NOT EXISTS jarvis_insights_schema.monthly_category_trends (
        trend_id UUID PRIMARY KEY,
        salary_cycle_id UUID,
        category_name TEXT,
        current_amount NUMERIC,
        previous_amount NUMERIC,
        change_percentage NUMERIC,
        created_at TIMESTAMP
    );
    """
}

class SupabaseDB:
    @staticmethod
    def get_connection():
        """Returns a new psycopg2 connection to Supabase Postgres."""
        url = settings.supabase_db_url
        if not url:
            raise ValueError("SUPABASE_DB_URL is not set in environment or settings.")
        return psycopg2.connect(url)

    @classmethod
    def initialize_supabase_database(cls) -> bool:
        """
        Attempts to create schema and tables on Supabase Postgres.
        Validates connection, DDL creation, and insert/update access.
        If any step fails, prints diagnostic logs and stops execution.
        """
        logger.info("Initializing Supabase Postgres Database...")
        
        conn = None
        current_step = ""
        current_sql = ""
        
        try:
            # 1. Connect
            current_step = "Establish Connection"
            conn = cls.get_connection()
            conn.autocommit = False
            cur = conn.cursor()
            
            # 2. Create Schema
            current_step = "Create Schema"
            current_sql = DDL_STATEMENTS["create_schema"]
            logger.info("Creating schema jarvis_insights_schema...")
            cur.execute(current_sql)
            
            # 3. Create Tables
            for table_name, ddl in DDL_STATEMENTS.items():
                if table_name == "create_schema":
                    continue
                current_step = f"Create Table: {table_name}"
                current_sql = ddl
                logger.info(f"Creating table jarvis_insights_schema.{table_name}...")
                cur.execute(current_sql)
                
            # 4. Validate Access (Write & Update Test on user_preferences)
            current_step = "Validate insert/update access"
            test_key = "test_connection_active"
            test_val = "true"
            
            # Insert Test
            current_sql = """
            INSERT INTO jarvis_insights_schema.user_preferences (preference_key, preference_value, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (preference_key) DO UPDATE
            SET preference_value = EXCLUDED.preference_value, updated_at = NOW();
            """
            cur.execute(current_sql, (test_key, test_val))
            
            # Update Test
            current_sql = """
            UPDATE jarvis_insights_schema.user_preferences
            SET preference_value = 'false', updated_at = NOW()
            WHERE preference_key = %s;
            """
            cur.execute(current_sql, (test_key,))
            
            # Clean up test row
            current_sql = "DELETE FROM jarvis_insights_schema.user_preferences WHERE preference_key = %s;"
            cur.execute(current_sql, (test_key,))
            
            conn.commit()
            cur.close()
            conn.close()
            logger.success("Supabase Postgres initialization and permissions check passed successfully!")
            return True
            
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            
            cls.report_failure_and_exit(current_step, current_sql, str(e))
            return False

    @classmethod
    def report_failure_and_exit(cls, step: str, failing_sql: str, error_msg: str):
        """Prints the exact failing SQL, error message, and DDL script, then exits."""
        print("\n" + "="*80)
        print("💥 CRITICAL ERROR: SUPABASE POSTGRES INITIALIZATION FAILED!")
        print("="*80)
        print(f"Failed during Step: {step}")
        print(f"Error Message    : {error_msg}")
        print("-"*80)
        if failing_sql:
            print("Failing SQL Query:")
            print(failing_sql.strip())
            print("-"*80)
        
        print("Please copy and execute the following DDL script inside your Supabase SQL Editor:")
        print("-"*80)
        full_ddl = []
        full_ddl.append(DDL_STATEMENTS["create_schema"])
        for tbl, ddl in DDL_STATEMENTS.items():
            if tbl != "create_schema":
                full_ddl.append(ddl.strip())
        print("\n\n".join(full_ddl))
        print("="*80 + "\n")
        
        # Force terminate backend run since it's the source of truth
        sys.exit(1)
