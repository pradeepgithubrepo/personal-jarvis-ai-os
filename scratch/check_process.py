import subprocess
res = subprocess.run(["ps", "aux"], capture_output=True, text=True)
with open("scratch/process_out.txt", "w") as f:
    f.write(res.stdout)
print("Done checking processes!")
