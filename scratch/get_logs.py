# scratch/get_logs.py

with open("logs/jarvis.log") as f:
    lines = f.readlines()

with open("scratch/matched_logs.txt", "w") as out:
    for line in lines[-150:]:
        if any(kw in line for kw in ["Stage", "complete", "Error", "failed", "crashed", "duplicate"]):
            out.write(line)
