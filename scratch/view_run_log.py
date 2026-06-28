# scratch/view_run_log.py

import os

log_dir = "/home/prad/.gemini/antigravity-ide/brain/ef803a59-6202-4076-866d-e74ef3179485/.system_generated/tasks/"
logs = [f for f in os.listdir(log_dir) if f.startswith("task-") and f.endswith(".log")]
logs.sort(key=lambda x: int(x.split("-")[1].split(".")[0]))

latest_log = os.path.join(log_dir, logs[-1])
print(f"Reading latest log: {latest_log}")

with open(latest_log) as f:
    for line in f:
        if "FYI Agent" in line or "Daily Brief Agent" in line or "Todo Agent" in line or "error" in line.lower() or "fail" in line.lower():
            print(line.strip())
