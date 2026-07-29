-- Phase 3D — Generic Vault Backend Migration
-- File: sql/migrations/phase3d_vault_module.sql

-- 1. Vault Categories Table
CREATE TABLE IF NOT EXISTS jarvis_insights_schemav1.vault_categories (
    vault_category_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_name     TEXT NOT NULL UNIQUE,
    display_order     INTEGER NOT NULL DEFAULT 0,
    icon              TEXT,
    color             TEXT,
    is_active         BOOLEAN NOT NULL DEFAULT TRUE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Vault Entries Table
CREATE TABLE IF NOT EXISTS jarvis_insights_schemav1.vault_entries (
    vault_entry_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vault_category_id  UUID NOT NULL REFERENCES jarvis_insights_schemav1.vault_categories(vault_category_id) ON DELETE CASCADE,
    parent_entry_id    UUID REFERENCES jarvis_insights_schemav1.vault_entries(vault_entry_id) ON DELETE CASCADE,
    owner              TEXT NOT NULL,
    title              TEXT NOT NULL,
    sub_category       TEXT,
    location           TEXT,
    access_information TEXT,
    notes              TEXT,
    sort_order         INTEGER NOT NULL DEFAULT 0,
    is_active          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_vault_categories_active_order 
    ON jarvis_insights_schemav1.vault_categories(is_active, display_order);

CREATE INDEX IF NOT EXISTS idx_vault_entries_category_id 
    ON jarvis_insights_schemav1.vault_entries(vault_category_id);

CREATE INDEX IF NOT EXISTS idx_vault_entries_parent_id 
    ON jarvis_insights_schemav1.vault_entries(parent_entry_id);

CREATE INDEX IF NOT EXISTS idx_vault_entries_owner 
    ON jarvis_insights_schemav1.vault_entries(owner);

-- 3. Seed Default Categories
INSERT INTO jarvis_insights_schemav1.vault_categories (category_name, display_order, icon, color) VALUES
    ('Bank Accounts', 1, 'land-bank', '#2563EB'),
    ('Stocks & Mutual Funds', 2, 'chart-trending-up', '#059669'),
    ('Long Term Investments', 3, 'vault', '#10B981'),
    ('Insurance', 4, 'shield-check', '#D97706'),
    ('Physical Assets', 5, 'home', '#7C3AED'),
    ('Investments', 6, 'chart-bar', '#059669'),
    ('Properties', 7, 'building', '#7C3AED'),
    ('Vehicles', 8, 'car', '#DC2626'),
    ('Documents', 9, 'file-text', '#4B5563'),
    ('Digital Accounts', 10, 'key', '#0891B2'),
    ('Other', 11, 'folder', '#6B7280')
ON CONFLICT (category_name) DO UPDATE SET
    display_order = EXCLUDED.display_order,
    icon = EXCLUDED.icon,
    color = EXCLUDED.color;

-- 4. Seed Spreadsheet Entries
INSERT INTO jarvis_insights_schemav1.vault_entries 
    (vault_category_id, owner, title, sub_category, location, access_information, notes, sort_order)
SELECT 
    vc.vault_category_id,
    e.owner,
    e.title,
    e.sub_category,
    e.location,
    e.access_information,
    e.notes,
    e.sort_order
FROM (VALUES
    ('Bank Accounts', 'Pradeep', 'HDFC - Pradeep', 'Personal Accounts', 'Ramapuram Branch', 'HDFC Bank', 'Norton password → HDFC', 1),
    ('Bank Accounts', 'Pradeep', 'ICICI - Pradeep', 'Personal Accounts', 'Virugambakkam Branch', 'ICICI Bank', 'Norton password → ICICI', 2),
    ('Bank Accounts', 'Pradeep', 'SBI - Pradeep', 'Personal Accounts', 'Ramanpudur - Nagercoil', 'SBI Bank', 'Norton password → SBI', 3),
    ('Bank Accounts', 'Shobana', 'HDFC - Shobana', 'Family Accounts', 'Ramapuram Branch', 'HDFC Bank', NULL, 4),
    ('Bank Accounts', 'Shobana', 'SBI - Shobana', 'Family Accounts', 'Nagercoil', 'SBI Bank', NULL, 5),
    ('Stocks & Mutual Funds', 'Pradeep', 'Stocks', 'Investment Types', 'Groww App', 'Groww', 'Norton password → Groww', 6),
    ('Stocks & Mutual Funds', 'Pradeep', 'Mutual Funds', 'Investment Types', 'ET Money App', 'ET Money', 'Norton password → ET Money', 7),
    ('Stocks & Mutual Funds', 'Pradeep', 'Kids Mutual funds', 'Investment Types', 'Groww App', 'Groww', 'Norton password → Groww', 8),
    ('Long Term Investments', 'Pradeep', 'Pension Fund Account', 'Pension', 'Retirement Fund', 'PF portal', 'Norton password', 9),
    ('Insurance', 'Pradeep', 'HDFC Family Floater', 'Health', '10 Lakhs Coverage', 'HDFC Insurance', 'Norton password', 10),
    ('Insurance', 'Pradeep', 'EY Corporate Health', 'Health', '10 Lakhs Coverage', 'Corporate Portal', 'Company Access', 11),
    ('Insurance', 'Pradeep', 'EY Corporate Term', 'Term', '1.5 Crore Coverage', 'Corporate Portal', 'Company Access', 12),
    ('Physical Assets', 'Pradeep', 'Sri Pattathuarasi Amman Flats', 'Real Estate', 'Property', 'Physical + Bank', '--', 13),
    ('Physical Assets', 'Pradeep', 'Kandigai Land', 'Real Estate', 'Land Asset', 'Physical Documents', '--', 14)
) AS e(cat_name, owner, title, sub_category, location, access_information, notes, sort_order)
JOIN jarvis_insights_schemav1.vault_categories vc ON vc.category_name = e.cat_name
WHERE NOT EXISTS (
    SELECT 1 FROM jarvis_insights_schemav1.vault_entries ve 
    WHERE ve.title = e.title AND ve.owner = e.owner
);
