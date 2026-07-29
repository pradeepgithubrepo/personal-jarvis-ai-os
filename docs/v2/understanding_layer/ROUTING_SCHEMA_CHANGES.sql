-- Phase 2B/V2.2 - Add route reason and confidence columns to signal_routes
-- File: docs/v2/understanding_layer/ROUTING_SCHEMA_CHANGES.sql

ALTER TABLE jarvis_insights_schemav1.signal_routes 
ADD COLUMN IF NOT EXISTS route_reason TEXT,
ADD COLUMN IF NOT EXISTS route_confidence DOUBLE PRECISION;
