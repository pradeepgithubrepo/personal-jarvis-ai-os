# Consumer Pipeline Forensic Report

## Executive Summary

A forensic review of the Jarvis Consumer Pipeline was conducted to determine why files remain unprocessed in the `jarvis-signals/incoming` Supabase Storage bucket. The investigation revealed the following critical findings:

1. **Scheduler Configuration Gap (Primary Root Cause):** The consumer pipeline (`consumer_sync`) has **not executed since July 9, 2026 at 17:10:38 UTC**. While the Windows Task Scheduler wakes the system and triggers [wakeup_launcher.ps1](file:///mnt/c/jarvis/JarvisScheduler/wakeup_launcher.ps1) successfully on schedule (latest run today, July 13, 2026), the launcher script is only configured to run the connectivity check script [verify_v1_connectivity.py](file:///home/user/petprojects/ai/jarvis/scripts/verify_v1_connectivity.py). It does not execute the actual consumer sync script [run_consumer.py](file:///home/user/petprojects/ai/jarvis/scripts/run_consumer.py).
2. **File Misrouting (Secondary Root Cause):** A bank statement PDF file (`5010XXXXXX3221_e5444aa8_01Apr2026_TO_30Jun2026_084431939.pdf`) was uploaded directly to the root `incoming/` directory instead of the designated `incoming/statements/` subfolder. Even if the consumer pipeline had been running, it would have skipped this file because the root orchestrator only discovers files ending with `.json`, and the bank statement collector only scans `incoming/statements/`.
3. **No Active Failures:** All 16 JSON files currently in `incoming/` are valid, parse successfully, and have unique hashes. They have never been seen or processed by any run of the consumer, and the deduplication and archiving systems are healthy.

---

## Investigation 1 – Current Incoming State

An inventory of the `jarvis-signals` storage bucket shows **17 files** sitting in the `incoming/` directory. No files exist in the `incoming/whatsapp/`, `incoming/sms/`, `incoming/gpay/`, or `incoming/statements/` subdirectories.

### File Inventory Table

| # | Filename | Size (Bytes) | Created Timestamp | File Type | JSON Parse | Target Collector / Routing |
|---|---|---|---|---|---|---|
| 1 | `5010XXXXXX3221_e5444aa8_01Apr2026_TO_30Jun2026_084431939.pdf` | 64,572 | 2026-07-13T03:16:17.428Z | PDF (Binary) | N/A (Failed UTF-8) | Bank Statement (Should be in `statements/` subfolder) |
| 2 | `user_1783643610948.json` | 439 | 2026-07-10T00:33:32.413Z | JSON | SUCCESS (1 signal) | Legacy Root Folder Processor |
| 3 | `user_1783671905889.json` | 2,506 | 2026-07-10T08:25:06.929Z | JSON | SUCCESS (8 signals) | Legacy Root Folder Processor |
| 4 | `user_1783698218000.json` | 2,617 | 2026-07-10T15:43:38.896Z | JSON | SUCCESS (2 signals) | Legacy Root Folder Processor |
| 5 | `user_1783758304991.json` | 6,321 | 2026-07-11T08:25:06.086Z | JSON | SUCCESS (16 signals) | Legacy Root Folder Processor |
| 6 | `user_1783783504741.json` | 6,454 | 2026-07-11T15:25:05.938Z | JSON | SUCCESS (16 signals) | Legacy Root Folder Processor |
| 7 | `user_1783815911734.json` | 888 | 2026-07-12T00:25:15.948Z | JSON | SUCCESS (2 signals) | Legacy Root Folder Processor |
| 8 | `user_1783845181697.json` | 9,501 | 2026-07-12T08:33:02.854Z | JSON | SUCCESS (29 signals) | Legacy Root Folder Processor |
| 9 | `user_1783870768644.json` | 11,164 | 2026-07-12T15:39:29.651Z | JSON | SUCCESS (35 signals) | Legacy Root Folder Processor |
| 10 | `user_1783902585344.json` | 519 | 2026-07-13T00:29:47.046Z | JSON | SUCCESS (1 signal) | Legacy Root Folder Processor |
| 11 | `user_1783931609096.json` | 4,164 | 2026-07-13T08:33:29.763Z | JSON | SUCCESS (13 signals) | Legacy Root Folder Processor |
| 12 | `family_member_1_1783655118573.json` | 777 | 2026-07-10T03:45:20.679Z | JSON | SUCCESS (2 signals) | Legacy Root Folder Processor |
| 13 | `family_member_1_1783698664749.json` | 1,927 | 2026-07-10T15:51:06.606Z | JSON | SUCCESS (4 signals) | Legacy Root Folder Processor |
| 14 | `family_member_1_1783846995046.json` | 5,447 | 2026-07-12T09:03:17.176Z | JSON | SUCCESS (12 signals) | Legacy Root Folder Processor |
| 15 | `family_member_1_1783871971855.json` | 5,956 | 2026-07-12T15:59:34.554Z | JSON | SUCCESS (16 signals) | Legacy Root Folder Processor |
| 16 | `family_member_1_1783904085638.json` | 432 | 2026-07-13T00:54:47.473Z | JSON | SUCCESS (1 signal) | Legacy Root Folder Processor |
| 17 | `family_member_1_1783931180799.json` | 1,736 | 2026-07-13T08:26:24.320Z | JSON | SUCCESS (4 signals) | Legacy Root Folder Processor |

---

## Investigation 2 – processed_files Cross Check

A complete hash correlation was run against the `processed_files` metadata table in Supabase.

* **Result:** **No matches found.** None of the 17 files currently sitting in `incoming/` have matching SHA-256 hashes or file names in the `processed_files` table.
* **Classification:**
  * All 16 JSON files: **UNSEEN** (Never discovered, never parsed, never registered).
  * 1 PDF bank statement: **UNSEEN** (Additionally, it suffers from a routing mismatch since it resides in the root `incoming/` directory instead of the `incoming/statements/` subfolder).

---

## Investigation 3 – Pipeline Run Correlation

The database `pipeline_runs` table shows that **consumer_sync has not run since July 9, 2026**.

* **Last Executed Run:** `run_id = c2c510fc-d932-48bf-8a83-281ece7efbe9`
  * **Trigger:** `MANUAL`
  * **Started At:** `2026-07-09T17:10:38.05772+00:00`
  * **Completed At:** `2026-07-09T17:10:40.664597+00:00`
  * **Status:** `SUCCESS`
  * **Metrics:** 0 files processed, 0 skipped, 0 failed (the bucket was empty).
* **Previous Major Ingestion Run:** `run_id = e891474c-a853-4f6b-8096-4d57756b3cfb`
  * **Started At:** `2026-07-09T16:44:35`
  * **Status:** `SUCCESS`
  * **Metrics:** 62 files processed, 1,713 signals created.
* **Correlation:** No run has ever seen or attempted to process any of the files listed in Investigation 1, because all these files were uploaded **after July 10, 2026**, which is at least 10 hours after the last consumer pipeline run.

---

## Investigation 4 – Dedup Logic Review

The deduplication logic prevents reprocessing files based on their SHA-256 hash.
* Since all 17 files are classified as **UNSEEN** and do not exist in the database, the deduplication engine has **not** rejected these files.
* Furthermore, all 17 files have unique SHA-256 hashes (no duplicate uploads within the current batch).
* **Conclusion:** The deduplication logic is idle but healthy. It has not contributed to the files remaining in `incoming/`.

---

## Investigation 5 – Archive Movement Review

A common failure mode is where a file is processed successfully (`processed_files` status is updated), but the storage movement to `archive/` fails, leaving the file stranded.
* **Analysis:** This has **not** occurred. No entry exists in `processed_files` for any of the 17 files, meaning no processing has occurred.
* **Conclusion:** The archiving mechanism has not run for these files and is not stuck in a half-completed state.

---

## Investigation 6 – Collector Review

Since the overall consumer pipeline orchestrator has not run, individual source collectors have also not been executed.
* **WhatsApp Collector:** 0 files discovered, 0 processed, 0 skipped, 0 failed.
* **SMS Collector:** 0 files discovered, 0 processed, 0 skipped, 0 failed.
* **GPay Collector:** 0 files discovered, 0 processed, 0 skipped, 0 failed.
* **Bank Statement Collector:** 0 files discovered, 0 processed, 0 skipped, 0 failed.

---

## Investigation 7 – WSL / Scheduler Correlation

The Windows host runs a scheduled task called `Jarvis Wake Validation` which wakes the system and triggers [wakeup_launcher.ps1](file:///mnt/c/jarvis/JarvisScheduler/wakeup_launcher.ps1).

### 1. Scheduler Health
The Windows Wake Scheduler is **healthy and executing reliably**. The host log `C:\jarvis\JarvisScheduler\logs\wakeup.log` shows scheduled wakeups occurring daily, with the latest run logged on July 13, 2026 at 18:20 local time (12:50 UTC).

### 2. Connectivity Script Execution
The `v1_connectivity_test` database table registers successful inserts at the exact timestamps logged by the scheduler:
* `2026-07-13T12:50:04.359855+00:00` (Files Found: 17)
* `2026-07-13T03:01:14.291888+00:00` (Files Found: 14)
* `2026-07-12T07:00:21.006637+00:00` (Files Found: 8)

### 3. The Scheduler Gap
An audit of [wakeup_launcher.ps1](file:///mnt/c/jarvis/JarvisScheduler/wakeup_launcher.ps1) reveals the root problem:

```powershell
# In wakeup_launcher.ps1:
$python = "/home/user/petprojects/ai/jarvis/.venv/bin/python"
$script = "/home/user/petprojects/ai/jarvis/scripts/verify_v1_connectivity.py"

$command = "$python $script"
```

The PowerShell script **only executes the validation script**, which counts the files in `incoming/` but does not process them. There is **no command** in `wakeup_launcher.ps1` to execute the consumer agent CLI [run_consumer.py](file:///home/user/petprojects/ai/jarvis/scripts/run_consumer.py).

---

## Investigation 8 – Root Cause Classification

Every file currently sitting in the `incoming/` directory is classified below:

| Path | SHA-256 Hash | Classification | Details |
|---|---|---|---|
| `incoming/5010XXXXXX3221_e5444aa8_01Apr2026_TO_30Jun2026_084431939.pdf` | `5704d8413bcf54...` | **NOT_SEEN** | Stranded in root folder instead of `incoming/statements/`. Unseen because consumer is not running. If consumer runs, this file will still be skipped due to incorrect folder/extension. |
| `incoming/user_1783643610948.json` | `e80beccea0db8e...` | **NOT_SEEN** | Unseen because consumer pipeline is not scheduled. |
| `incoming/user_1783671905889.json` | `9687308937ce19...` | **NOT_SEEN** | Unseen because consumer pipeline is not scheduled. |
| `incoming/user_1783698218000.json` | `fab894504a2b78...` | **NOT_SEEN** | Unseen because consumer pipeline is not scheduled. |
| `incoming/user_1783758304991.json` | `3b38306bd5151b...` | **NOT_SEEN** | Unseen because consumer pipeline is not scheduled. |
| `incoming/user_1783783504741.json` | `207ffe77aaa4b4...` | **NOT_SEEN** | Unseen because consumer pipeline is not scheduled. |
| `incoming/user_1783815911734.json` | `f0bf796a5f08af...` | **NOT_SEEN** | Unseen because consumer pipeline is not scheduled. |
| `incoming/user_1783845181697.json` | `54a2be0a74d940...` | **NOT_SEEN** | Unseen because consumer pipeline is not scheduled. |
| `incoming/user_1783870768644.json` | `2b0acb067a720f...` | **NOT_SEEN** | Unseen because consumer pipeline is not scheduled. |
| `incoming/user_1783902585344.json` | `fb5391c781a64c...` | **NOT_SEEN** | Unseen because consumer pipeline is not scheduled. |
| `incoming/user_1783931609096.json` | `c99cfe673d6c25...` | **NOT_SEEN** | Unseen because consumer pipeline is not scheduled. |
| `incoming/family_member_1_1783655118573.json` | `05060a19444905...` | **NOT_SEEN** | Unseen because consumer pipeline is not scheduled. |
| `incoming/family_member_1_1783698664749.json` | `c81eaf0bd10b80...` | **NOT_SEEN** | Unseen because consumer pipeline is not scheduled. |
| `incoming/family_member_1_1783846995046.json` | `b6bb9213e208f0...` | **NOT_SEEN** | Unseen because consumer pipeline is not scheduled. |
| `incoming/family_member_1_1783871971855.json` | `e2e82dd9b18996...` | **NOT_SEEN** | Unseen because consumer pipeline is not scheduled. |
| `incoming/family_member_1_1783904085638.json` | `4034524c5825fb...` | **NOT_SEEN** | Unseen because consumer pipeline is not scheduled. |
| `incoming/family_member_1_1783931180799.json` | `0917a22cb2bc8d...` | **NOT_SEEN** | Unseen because consumer pipeline is not scheduled. |

---

## Conclusion & Health Status

* **Why is each file still in incoming?**
  * The 16 JSON files are still in `incoming/` because the consumer pipeline hasn't run since they were uploaded.
  * The PDF statement is in `incoming/` because it was uploaded to the wrong folder (it should be in `incoming/statements/`) and the consumer is not running.
* **Is the consumer healthy?**
  * Yes. The local parser and consumer pipeline codebase are healthy, and the previous run on July 9 processed 62 files without issues. However, the consumer is **operationally inactive** on the live scheduler.
* **Is the deduplication logic working?**
  * Yes, it is fully functional but currently idle since it hasn't received new hashes to filter.
* **Is the archive logic working?**
  * Yes, functional but idle.
* **Is the scheduler execution reliable?**
  * Yes. The Windows Task Scheduler triggers the WSL environment perfectly. The gap lies in the **task definition**, which fails to call `run_consumer.py`.

---

## Next Steps (Recommendations for recovery)

> [!WARNING]
> Do not execute these steps yet. As per the constraints of this task, no actions or fixes should be taken during this phase.

1. **Move PDF Statement:** Relocate the bank statement `5010XXXXXX3221_e5444aa8_01Apr2026_TO_30Jun2026_084431939.pdf` from `incoming/` to `incoming/statements/`.
2. **Update Scheduler Launcher:** Modify [wakeup_launcher.ps1](file:///mnt/c/jarvis/JarvisScheduler/wakeup_launcher.ps1) to execute both the connectivity check and the consumer sync:
   ```powershell
   # Add to wakeup_launcher.ps1:
   $consumerScript = "/home/user/petprojects/ai/jarvis/scripts/run_consumer.py"
   $consumerCommand = "$python $consumerScript --trigger SCHEDULED"
   # Execute consumer command
   ```
