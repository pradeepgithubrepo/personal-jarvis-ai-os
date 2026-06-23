@echo off
echo ==================================================
echo Launching Jarvis Processing Pipeline inside WSL...
echo ==================================================
wsl.exe bash -c "cd /home/prad/petprojects/ai/jarvis && /home/prad/petprojects/ai/jarvis/.venv/bin/python scripts/run_full_pipeline.py"

echo Pipeline finished (exit code %ERRORLEVEL%). Putting laptop back to sleep...
powershell -Command "Add-Type -Assembly System.Windows.Forms; [System.Windows.Forms.Application]::SetSuspendState([System.Windows.Forms.PowerState]::Suspend, $false, $false)"

