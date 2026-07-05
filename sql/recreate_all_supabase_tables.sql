CREATE SCHEMA IF NOT EXISTS jarvis_insights_schema;
SET search_path TO jarvis_insights_schema;
DROP TABLE IF EXISTS jarvis_insights_schema.signals CASCADE;
CREATE TABLE IF NOT EXISTS jarvis_insights_schema.signals (
	id BIGSERIAL, 
	source VARCHAR(50) NOT NULL, 
	signal_type VARCHAR(100) NOT NULL, 
	category VARCHAR(100) NOT NULL, 
	importance VARCHAR(50) NOT NULL, 
	summary VARCHAR(1000) NOT NULL, 
	raw_json TEXT, 
	created_at TIMESTAMPTZ NOT NULL, message_id VARCHAR(255), 
	PRIMARY KEY (id)
);

DROP TABLE IF EXISTS jarvis_insights_schema.mobile_signals CASCADE;
CREATE TABLE IF NOT EXISTS jarvis_insights_schema.mobile_signals (
	id BIGSERIAL, 
	device_id VARCHAR(100) NOT NULL, 
	source VARCHAR(50) NOT NULL, 
	sender VARCHAR(500) NOT NULL, 
	message TEXT NOT NULL, 
	mobile_timestamp VARCHAR(100) NOT NULL, 
	processed BOOLEAN NOT NULL, 
	created_at TIMESTAMPTZ NOT NULL, message_hash VARCHAR(64), 
	PRIMARY KEY (id)
);

DROP TABLE IF EXISTS jarvis_insights_schema.qualified_signals CASCADE;
CREATE TABLE IF NOT EXISTS jarvis_insights_schema.qualified_signals (
	id BIGSERIAL, 
	signal_id VARCHAR(100) NOT NULL, 
	source VARCHAR(50) NOT NULL, 
	sender VARCHAR(500) NOT NULL, 
	message TEXT NOT NULL, 
	timestamp TIMESTAMPTZ NOT NULL, 
	qualification_score INTEGER NOT NULL, 
	qualification_status VARCHAR(50) NOT NULL, 
	qualification_reason VARCHAR(100), 
	created_at TIMESTAMPTZ NOT NULL, 
	PRIMARY KEY (id)
);

DROP TABLE IF EXISTS jarvis_insights_schema.understood_signals CASCADE;
CREATE TABLE IF NOT EXISTS jarvis_insights_schema.understood_signals (
	id VARCHAR(100) NOT NULL, 
	qualified_signal_id BIGINT NOT NULL, 
	raw_signal_id VARCHAR(100) NOT NULL, 
	signal_type VARCHAR(50) NOT NULL, 
	importance VARCHAR(20) NOT NULL, 
	confidence NUMERIC NOT NULL, 
	summary TEXT NOT NULL, 
	reason TEXT, 
	processing_path VARCHAR(20) NOT NULL, 
	llm_model_used VARCHAR(50) NOT NULL, 
	contract_json TEXT NOT NULL, 
	is_verified BOOLEAN NOT NULL, 
	created_at TIMESTAMPTZ NOT NULL, 
	PRIMARY KEY (id)
);

DROP TABLE IF EXISTS jarvis_insights_schema.financial_events CASCADE;
CREATE TABLE IF NOT EXISTS jarvis_insights_schema.financial_events (
	id BIGSERIAL, 
	title VARCHAR(500) NOT NULL, 
	amount NUMERIC, 
	currency VARCHAR(10), 
	transaction_type VARCHAR(50) NOT NULL, 
	payment_channel VARCHAR(50), 
	paid_to VARCHAR(255), 
	paid_from VARCHAR(255), 
	transaction_id VARCHAR(255), 
	event_date TIMESTAMPTZ, 
	source_signal_id INTEGER NOT NULL, 
	created_at TIMESTAMPTZ NOT NULL, category VARCHAR(100), 
	PRIMARY KEY (id)
);

DROP TABLE IF EXISTS jarvis_insights_schema.financial_facts CASCADE;
CREATE TABLE IF NOT EXISTS jarvis_insights_schema.financial_facts (
	id VARCHAR(36) NOT NULL, 
	fact_type VARCHAR(30) NOT NULL, 
	financial_event_id BIGINT NOT NULL, 
	understood_signal_id VARCHAR(36), 
	qualified_signal_id BIGINT, 
	amount NUMERIC NOT NULL, 
	currency VARCHAR(10) NOT NULL, 
	merchant_raw VARCHAR(255), 
	merchant_canonical VARCHAR(200), 
	merchant_id VARCHAR(36), 
	category VARCHAR(50), 
	classification_confidence NUMERIC NOT NULL, 
	classification_method VARCHAR(30), 
	event_date DATE, 
	month DATE, 
	is_excluded_from_accounting_spend BOOLEAN NOT NULL, 
	is_excluded_from_lifestyle_spend BOOLEAN NOT NULL, 
	exclusion_reason VARCHAR(100), 
	refund_of_fact_id VARCHAR(36), 
	is_refunded BOOLEAN NOT NULL, 
	refund_applied_to_month DATE, 
	salary_source_id VARCHAR(36), 
	transfer_pair_id VARCHAR(36), 
	created_at TIMESTAMPTZ NOT NULL, 
	PRIMARY KEY (id)
);

DROP TABLE IF EXISTS jarvis_insights_schema.salary_events CASCADE;
CREATE TABLE IF NOT EXISTS jarvis_insights_schema.salary_events (
	id VARCHAR(36) NOT NULL, 
	financial_event_id BIGINT NOT NULL, 
	salary_source_id VARCHAR(36), 
	detected_employer VARCHAR(200), 
	gross_amount NUMERIC NOT NULL, 
	currency VARCHAR(10) NOT NULL, 
	salary_month DATE NOT NULL, 
	detection_method VARCHAR(30) NOT NULL, 
	confidence NUMERIC NOT NULL, 
	detected_at TIMESTAMPTZ NOT NULL, 
	PRIMARY KEY (id)
);

DROP TABLE IF EXISTS jarvis_insights_schema.salary_sources CASCADE;
CREATE TABLE IF NOT EXISTS jarvis_insights_schema.salary_sources (
	id VARCHAR(36) NOT NULL, 
	canonical_name VARCHAR(200) NOT NULL, 
	aliases JSONB NOT NULL, 
	employment_type VARCHAR(20) NOT NULL, 
	expected_day_of_month INTEGER, 
	day_tolerance INTEGER NOT NULL, 
	expected_amount NUMERIC, 
	amount_tolerance_pct NUMERIC NOT NULL, 
	source_bank_aliases JSONB NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	pending_review BOOLEAN NOT NULL, 
	first_detected DATE, 
	last_seen DATE, 
	detection_history JSONB NOT NULL, 
	created_at TIMESTAMPTZ NOT NULL, 
	updated_at TIMESTAMPTZ NOT NULL, 
	PRIMARY KEY (id)
);

DROP TABLE IF EXISTS jarvis_insights_schema.merchant_profiles CASCADE;
CREATE TABLE IF NOT EXISTS jarvis_insights_schema.merchant_profiles (
	id VARCHAR(36) NOT NULL, 
	merchant_id VARCHAR(36) NOT NULL, 
	lifetime_spend NUMERIC NOT NULL, 
	avg_transaction_value NUMERIC NOT NULL, 
	total_transaction_count INTEGER NOT NULL, 
	visit_count_last_30d INTEGER NOT NULL, 
	visit_count_last_90d INTEGER NOT NULL, 
	last_transaction_date DATE, 
	last_transaction_amount NUMERIC, 
	updated_at TIMESTAMPTZ NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (merchant_id)
);

DROP TABLE IF EXISTS jarvis_insights_schema.bank_accounts CASCADE;
CREATE TABLE IF NOT EXISTS jarvis_insights_schema.bank_accounts (
	id VARCHAR(36) NOT NULL, 
	bank_name VARCHAR(100) NOT NULL, 
	ifsc_prefix VARCHAR(10), 
	account_number_masked VARCHAR(20), 
	account_type VARCHAR(20) NOT NULL, 
	sender_aliases JSONB NOT NULL, 
	receiver_aliases JSONB NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	registered_at TIMESTAMPTZ NOT NULL, 
	updated_at TIMESTAMPTZ NOT NULL, 
	PRIMARY KEY (id)
);

DROP TABLE IF EXISTS jarvis_insights_schema.merchants CASCADE;
CREATE TABLE IF NOT EXISTS jarvis_insights_schema.merchants (
	id VARCHAR(36) NOT NULL, 
	canonical_name VARCHAR(200) NOT NULL, 
	category VARCHAR(50) NOT NULL, 
	aliases JSONB NOT NULL, 
	logo_url VARCHAR(500), 
	is_trusted BOOLEAN NOT NULL, 
	is_seed BOOLEAN NOT NULL, 
	created_at TIMESTAMPTZ NOT NULL, 
	updated_at TIMESTAMPTZ NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (canonical_name)
);

DROP TABLE IF EXISTS jarvis_insights_schema.runtime_events CASCADE;
CREATE TABLE IF NOT EXISTS jarvis_insights_schema.runtime_events (
	id BIGSERIAL, 
	event_type VARCHAR(100) NOT NULL, 
	source VARCHAR(100) NOT NULL, 
	payload TEXT NOT NULL, 
	status VARCHAR(50) NOT NULL, 
	created_at TIMESTAMPTZ NOT NULL, 
	PRIMARY KEY (id)
);

DROP TABLE IF EXISTS jarvis_insights_schema.transfer_pairs CASCADE;
CREATE TABLE IF NOT EXISTS jarvis_insights_schema.transfer_pairs (
	id VARCHAR(36) NOT NULL, 
	debit_event_id INTEGER NOT NULL, 
	credit_event_id INTEGER NOT NULL, 
	amount NUMERIC NOT NULL, 
	currency VARCHAR(10) NOT NULL, 
	transfer_type VARCHAR(20) NOT NULL, 
	window_seconds NUMERIC, 
	confidence NUMERIC NOT NULL, 
	detected_at TIMESTAMPTZ NOT NULL, 
	PRIMARY KEY (id)
);

DROP TABLE IF EXISTS jarvis_insights_schema.facts CASCADE;
CREATE TABLE IF NOT EXISTS jarvis_insights_schema.facts (
	fact_id VARCHAR(36) NOT NULL, 
	fact_type VARCHAR(50) NOT NULL, 
	fact_value JSONB NOT NULL, 
	confidence NUMERIC NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	owner_agent VARCHAR(50), 
	source_agent VARCHAR(50) NOT NULL, 
	source_type VARCHAR(30) NOT NULL, 
	first_seen TIMESTAMPTZ NOT NULL, 
	last_seen TIMESTAMPTZ NOT NULL, 
	evidence JSONB, 
	created_at TIMESTAMPTZ NOT NULL, 
	updated_at TIMESTAMPTZ NOT NULL, 
	PRIMARY KEY (fact_id)
);

DROP TABLE IF EXISTS jarvis_insights_schema.fact_relationships CASCADE;
CREATE TABLE IF NOT EXISTS jarvis_insights_schema.fact_relationships (
	id BIGSERIAL, 
	subject_id VARCHAR(36) NOT NULL, 
	predicate VARCHAR(50) NOT NULL, 
	object_id VARCHAR(36) NOT NULL, 
	confidence NUMERIC NOT NULL, 
	created_at TIMESTAMPTZ NOT NULL, 
	updated_at TIMESTAMPTZ NOT NULL, 
	PRIMARY KEY (id)
);

DROP TABLE IF EXISTS jarvis_insights_schema.todo_items CASCADE;
CREATE TABLE IF NOT EXISTS jarvis_insights_schema.todo_items (
	todo_id VARCHAR(36) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	description TEXT, 
	category VARCHAR(30) NOT NULL, 
	priority VARCHAR(20) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	due_date TIMESTAMPTZ, 
	source_agent VARCHAR(50) NOT NULL, 
	source_reference JSONB, 
	confidence NUMERIC NOT NULL, 
	created_at TIMESTAMPTZ NOT NULL, 
	updated_at TIMESTAMPTZ NOT NULL, 
	PRIMARY KEY (todo_id)
);

DROP TABLE IF EXISTS jarvis_insights_schema.fyi_events CASCADE;
CREATE TABLE IF NOT EXISTS jarvis_insights_schema.fyi_events (
	event_id VARCHAR(36) NOT NULL, 
	event_type VARCHAR(100) NOT NULL, 
	category VARCHAR(50) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	description TEXT, 
	importance VARCHAR(20) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	source_signal_id VARCHAR(36), 
	duplicate_count INTEGER NOT NULL, 
	created_at TIMESTAMPTZ NOT NULL, 
	updated_at TIMESTAMPTZ NOT NULL, 
	PRIMARY KEY (event_id)
);

DROP TABLE IF EXISTS jarvis_insights_schema.daily_briefs CASCADE;
CREATE TABLE IF NOT EXISTS jarvis_insights_schema.daily_briefs (
	brief_id VARCHAR(36) NOT NULL, 
	brief_type VARCHAR(50) NOT NULL, 
	generated_at TIMESTAMPTZ NOT NULL, 
	content TEXT NOT NULL, 
	todo_count INTEGER NOT NULL, 
	fyi_count INTEGER NOT NULL, 
	fact_count INTEGER NOT NULL, 
	payload_json TEXT, 
	PRIMARY KEY (brief_id)
);

DROP TABLE IF EXISTS jarvis_insights_schema.monthly_spending_summary CASCADE;
CREATE TABLE IF NOT EXISTS jarvis_insights_schema.monthly_spending_summary (
	summary_id VARCHAR(36) NOT NULL, 
	month_key VARCHAR(7) NOT NULL, 
	total_spend NUMERIC NOT NULL, 
	transaction_count INTEGER NOT NULL, 
	created_at TIMESTAMPTZ NOT NULL, 
	updated_at TIMESTAMPTZ NOT NULL, total_debits NUMERIC NOT NULL DEFAULT 0.0, total_credits NUMERIC NOT NULL DEFAULT 0.0, accounting_spend NUMERIC NOT NULL DEFAULT 0.0, lifestyle_spend NUMERIC NOT NULL DEFAULT 0.0, total_income NUMERIC NOT NULL DEFAULT 0.0, net_cash_flow NUMERIC NOT NULL DEFAULT 0.0, internal_transfers NUMERIC NOT NULL DEFAULT 0.0, insurance_premiums NUMERIC NOT NULL DEFAULT 0.0, investments NUMERIC NOT NULL DEFAULT 0.0, refund_offsets NUMERIC NOT NULL DEFAULT 0.0, 
	PRIMARY KEY (summary_id), 
	UNIQUE (month_key)
);

DROP TABLE IF EXISTS jarvis_insights_schema.monthly_category_spend CASCADE;
CREATE TABLE IF NOT EXISTS jarvis_insights_schema.monthly_category_spend (
	entry_id VARCHAR(36) NOT NULL, 
	month_key VARCHAR(7) NOT NULL, 
	category_name VARCHAR(100) NOT NULL, 
	amount NUMERIC NOT NULL, 
	transaction_count INTEGER NOT NULL, 
	created_at TIMESTAMPTZ NOT NULL, 
	PRIMARY KEY (entry_id), 
	CONSTRAINT uq_month_category UNIQUE (month_key, category_name)
);

DROP TABLE IF EXISTS jarvis_insights_schema.monthly_category_trends CASCADE;
CREATE TABLE IF NOT EXISTS jarvis_insights_schema.monthly_category_trends (
	trend_id VARCHAR(36) NOT NULL, 
	month_key VARCHAR(7) NOT NULL, 
	category_name VARCHAR(100) NOT NULL, 
	current_amount NUMERIC NOT NULL, 
	previous_amount NUMERIC NOT NULL, 
	change_percentage NUMERIC NOT NULL, 
	created_at TIMESTAMPTZ NOT NULL, 
	PRIMARY KEY (trend_id), 
	CONSTRAINT uq_trend_month_category UNIQUE (month_key, category_name)
);
