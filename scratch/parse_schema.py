# scratch/parse_schema.py

import json

with open("scratch/supabase_schema.json") as f:
    schema = json.load(f)

for table, defs in sorted(schema.items()):
    print(f"Table: {table}")
    properties = defs.get("properties", {})
    required = defs.get("required", [])
    for col, props in sorted(properties.items()):
        col_type = props.get("type")
        col_format = props.get("format", "")
        req_str = "REQUIRED" if col in required else "NULLABLE"
        print(f"  Column: {col} | Type: {col_type} ({col_format}) | {req_str}")
    print()
