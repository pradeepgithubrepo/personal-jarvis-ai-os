# Lessons Learned — Phase 1B Source Collectors

This document summarizes the technical challenges, blockers, and solutions discovered during the implementation and validation of Phase 1B.

---

## 1. WSL2 Blocking Hostname resolution (Priority 1)

### Challenge
The initial pipeline run was hanging indefinitely during the `agent.start_run` invocation. 

### Cause
In WSL2 (Linux on Windows), `socket.gethostname()` and `getpass.getuser()` make resolver calls to bind the local hostname. If the nameserver configured in `/etc/resolv.conf` becomes unreachable (e.g. after Windows goes to sleep or switches Wi-Fi networks), this system call hangs indefinitely (waiting for resolver socket timeouts), stalling the thread.

### Solution
Instead of making blocking network name resolutions, we bypassed the sockets layer entirely:
1. **Hostname:** Read directly from the POSIX proc filesystem (`/proc/sys/kernel/hostname`) which is a local, non-blocking memory lookup (taking 0.000s). Fall back to the environment variable `HOSTNAME`.
2. **User:** Checked environment variables `USER` and `USERNAME` (taking 0.000s) before falling back to `getpass`.

---

## 2. API Connection Latency & Bulk Upsert (Priority 3)

### Challenge
The GPay test case (278 transactions) and the Mixed Batch test case (330 transactions) were exceeding the 60-second execution timeout.

### Cause
Inserting transactions sequentially via PostgREST makes one HTTP request per transaction. Across the WAN, 330 HTTP requests create a massive network latency bottleneck (taking 50-80 seconds).

### Solution
We implemented a high-performance bulk write method `persist_signals_bulk`:
1. **Local Deduplication:** Filters duplicates locally using memory sets of message hashes before contacting the database.
2. **Bulk Upsert:** Performs a single PostgREST `upsert` call with the unique records. This reduces 330 requests down to 1 query, completing in under 0.5s.
3. **Resilient Fallback:** If the bulk upsert fails due to schema conflicts, it falls back to safe sequential inserts, logging duplicate warnings.

---

## 3. HDFC Contact_7nce CR Indicator Layout

### Challenge
The HDFC statement parser was initially classifying credit transactions as debits during mock validation.

### Cause
HDFC statement tables align the credit/debit indicators (`CR`) to the end of the contact_7nce column (`1,000.00CR`) instead of the transaction description. Scanning the narration string alone missed the credit marker.

### Solution
Updated the regex to match the entire line-level string, allowing the HDFC parser to inspect the contact_7nce segment for `CR` tags.
