-- scripts/migration/update_fyi_importance.sql
-- Run this script in the Supabase SQL Editor to migrate the schema for FYI Agent V2

BEGIN;

-- 1. Create fyi_importance_level ENUM conditionally
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'fyi_importance_level') THEN
        CREATE TYPE jarvis_insights_schemav1.fyi_importance_level AS ENUM (
            'CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'EPHEMERAL'
        );
    END IF;
END$$;

-- 2. Add importance_level column to information_items
ALTER TABLE jarvis_insights_schemav1.information_items 
ADD COLUMN IF NOT EXISTS importance_level jarvis_insights_schemav1.fyi_importance_level DEFAULT 'MEDIUM'::jarvis_insights_schemav1.fyi_importance_level NOT NULL;

-- 3. Modify category check constraint
-- First drop the check constraint on category if it exists
ALTER TABLE jarvis_insights_schemav1.information_items DROP CONSTRAINT IF EXISTS information_items_category_check;
ALTER TABLE jarvis_insights_schemav1.information_items ADD CONSTRAINT information_items_category_check CHECK (
    category IN ('TRAVEL', 'ORDER_TRACKING', 'SECURITY_ALERT', 'FAMILY_SCHOOL', 'UTILITY_INFO', 'GENERAL', 'HEALTH', 'FINANCE_INSURANCE')
);

-- 4. Create index on importance_level
CREATE INDEX IF NOT EXISTS idx_info_items_importance ON jarvis_insights_schemav1.information_items(importance_level);

COMMIT;
