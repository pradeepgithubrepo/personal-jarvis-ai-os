import csv

csv_path = "docs/v2/understanding_layer/WHATSAPP_REVIEW_DUMP.csv"

yes_rows = []
with open(csv_path, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        comment = row.get("pradeep review comments - yes / no", "").strip()
        if comment.lower() not in ["no", ""]:
            yes_rows.append((row["sender"], row["message"], comment))

print(f"Total rows marked YES: {len(yes_rows)}")
for idx, (sender, message, comment) in enumerate(yes_rows):
    print(f"{idx+1}. Sender: {sender}")
    print(f"   Message: {message}")
    print(f"   Comment: {comment}")
