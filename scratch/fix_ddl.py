# scratch/fix_ddl.py

with open("sql/recreate_all_supabase_tables.sql") as f:
    sql = f.read()

# Replace types
sql = sql.replace("\tid INTEGER NOT NULL,", "\tid BIGSERIAL,")
sql = sql.replace("\tfinancial_event_id INTEGER NOT NULL,", "\tfinancial_event_id BIGINT NOT NULL,")
sql = sql.replace("\tqualified_signal_id INTEGER NOT NULL,", "\tqualified_signal_id BIGINT NOT NULL,")
sql = sql.replace("\tqualified_signal_id INTEGER,", "\tqualified_signal_id BIGINT,")

with open("sql/recreate_all_supabase_tables.sql", "w") as f:
    f.write(sql)

print("DDL script fixed with auto-increment BIGSERIAL properties!")
