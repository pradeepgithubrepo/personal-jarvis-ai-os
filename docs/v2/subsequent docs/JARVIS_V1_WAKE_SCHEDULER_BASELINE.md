# Jarvis V1 – Windows Wake Scheduler Configuration (Baseline Locked)

## Purpose

This document defines the validated and working configuration used to wake the Jarvis host machine and execute the Jarvis connectivity validation process automatically.

This configuration has been successfully tested and should be treated as the baseline for future Jarvis automation.

---

# Objective

Execute Jarvis scheduled jobs at:

```text
06:00 AM
12:30 PM
07:30 PM
```

while the laptop is unattended.

The execution flow is:

```text
Task Scheduler
    ↓
Wake Timer
    ↓
Windows Resume
    ↓
WSL Startup
    ↓
Python Execution
    ↓
Supabase Connectivity Validation
    ↓
Storage Read
    ↓
Database Insert
```

---

# Host Environment

## Operating System

```text
Windows 11
```

## Linux Runtime

```text
WSL2
Ubuntu
```

## Jarvis Runtime Location

```text
/home/prad/petprojects/ai/jarvis
```

## Validation Script

[verify_v1_connectivity.py](file:///home/prad/petprojects/ai/jarvis/scripts/verify_v1_connectivity.py)

---

# Important Finding

## Modern Standby (S0) Is Not Reliable

System capability:

```cmd
powercfg /a
```

Result:

```text
Standby (S0 Low Power Idle)
```

Observed behaviour:

```text
Sleep
    ↓
Wake timer registered
    ↓
Machine frequently fails to wake
    ↓
Task executes only when user opens lid
```

Conclusion:

```text
DO NOT rely on S0 Sleep for Jarvis scheduling.
```

---

# Validated Solution

## Hibernate

The following configuration was successfully validated.

### Manual Hibernate

Command:

```cmd
shutdown /h
```

Result:

```text
Machine hibernates
Wake timer fires
Jarvis task executes
Supabase insert succeeds
```

### Lid Close Hibernate

Result:

```text
Close Lid
    ↓
Hibernate
    ↓
Wake timer fires
    ↓
Jarvis executes successfully
```

This behaviour has been confirmed.

---

# Power Configuration

## Lid Close Action

Control Panel

```text
Power Options
    ↓
Choose what closing the lid does
```

Configuration:

```text
On Battery  = Hibernate
Plugged In  = Hibernate
```

Status:

```text
VALIDATED
```

---

## Sleep Timer

Current configuration:

```text
Battery   = 20 minutes
AC Power  = 2 hours
```

Recommended Jarvis configuration:

```text
Battery   = Never
AC Power  = Never
```

Reason:

```text
Avoid accidental transition into S0 Modern Standby.
Use Hibernate only.
```

---

# Scheduled Task

## Task Name

```text
Jarvis Wake Validation V1
```

---

## General

```text
Run whether user is logged on or not
Run with highest privileges
User = pprad
```

Important:

```text
NEVER run as SYSTEM
```

Reason:

```text
WSL distributions are user scoped.

SYSTEM execution causes:

WSL_E_LOCAL_SYSTEM_NOT_SUPPORTED
```

---

## Triggers

### Trigger 1

```text
06:00 AM
Daily
```

### Trigger 2

```text
12:30 PM
Daily
```

### Trigger 3

```text
07:30 PM
Daily
```

---

## Action

Program:

```text
powershell.exe
```

Arguments:

```text
-ExecutionPolicy Bypass -File "C:\jarvis\JarvisScheduler\wakeup_launcher.ps1"
```

---

## Conditions

Enabled:

```text
Wake the computer to run this task
```

---

## Settings

Enabled:

```text
Allow task to be run on demand

Run task as soon as possible after a scheduled start is missed

If task is already running:
    Do not start a new instance
```

Disabled:

```text
Automatic retries
```

---

# Wake Timer Verification

Validate timer registration:

```cmd
powercfg /waketimers
```

Expected:

```text
Windows will execute
'NT TASK\Jarvis Wake Validation V1'
scheduled task that requested waking the computer.
```

---

# Wake Verification

Validate last wake source:

```cmd
powercfg /lastwake
```

Useful when troubleshooting missed executions.

---

# Validation Success Criteria

A successful execution produces:

```text
Triggered
User=pprad
Computer=PRADEEP

WSL Ready

Executing:
/home/prad/petprojects/ai/jarvis/.venv/bin/python
/home/prad/petprojects/ai/jarvis/scripts/verify_v1_connectivity.py

Starting Validation
Loading Environment
Supabase Connected
Bucket Read Success

Insert Success

Validation Complete

DATABASE INSERT CONFIRMED

Completed Successfully
```

---

# Database Validation

Table:

```text
jarvis_insights_schemav1.v1_connectivity_test
```

Expected record:

```text
test_message = Jarvis Wake Validation

file_count = <current bucket count>

execution_time = <utc timestamp>
```

---

# Operational Decision (Locked)

For Jarvis V1:

```text
Use Hibernate
Use Wake Timers
Use Task Scheduler
Use User Context (pprad)
Do NOT rely on S0 Sleep
Do NOT run WSL under SYSTEM
```

Status:

```text
VALIDATED
LOCKED BASELINE
READY FOR DAILY OPERATION
```

This should be treated as the reference implementation for all future Jarvis scheduled jobs (Daily Brief, Midday Sync, Evening Wrap-up, signal processing, and future agent orchestration tasks). 🚀
