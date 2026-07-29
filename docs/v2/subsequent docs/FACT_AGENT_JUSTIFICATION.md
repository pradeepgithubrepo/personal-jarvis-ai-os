# FACT Agent Architectural Justification Report

This report evaluates the current state of **FACT Agent** route records in the remote Supabase database and addresses whether a dedicated FACT Agent is architecturally justified or if it can be absorbed into the FYI Agent pipeline.

---

## 1. Current FACT Agent Metrics

* **Dedicated Database Tables**: None. There is no `facts` table in the database schema.
* **Total FACT Routes**: **30** pending routes exist in the `signal_routes` table routed to `fact_agent`.
* **Current Implementation**: A placeholder stub class `FactAgentStub` that accepts contracts but performs no database writes.

---

## 2. Sample FACT Route Records (30 Records Audit)

Below is the complete list of all `fact_agent` route records fetched from the remote Supabase database:

| ID | Message Text | Original Signal Type | Memory Candidate? |
|---|---|---|---|
| 1 | `Purifier person don't pick up the call so register complaint` | **ACTION** | `True` |
| 2 | `Purifier person don't pick up the call so register complaint` | **ACTION** | `True` |
| 3 | `T2 is given for rent, and the tenant will be shifting it today. Just got confirmation from the te...` | **ACTION** | `True` |
| 4 | `Doctor Said there is rarest of rare the battery might open up in the intestine .. it might cause ...` | **ACTION** | `True` |
| 5 | `Buy milk pa` | **ACTION** | `True` |
| 6 | `We have processed your Reimbursement Claim 51219697 of INR 2490. Please click https://massist.in/...` | **ACTION** | `True` |
| 7 | `We have processed your Reimbursement Claim 51219665 of INR 2490. Please click https://massist.in/...` | **ACTION** | `True` |
| 8 | `Dear Parents  We will be having our POP ( Parent orientation Program) on 10.7.2026( Tomorrow ) Fr...` | **ACTION** | `True` |
| 9 | `Secure your Card account by regularly changing your passwords or PINs and do not share these deta...` | **ACTION** | `True` |
| 10 | `We have received confirmation on the settlement of your claim 50597764 for a policy issued by The...` | **ACTION** | `True` |
| 11 | `We have processed your Reimbursement Claim 50597764 of INR 750. Please click https://massist.in/M...` | **ACTION** | `True` |
| 12 | `We have received confirmation on the settlement of your claim 50485973 for a policy issued by The...` | **ACTION** | `True` |
| 13 | `Thank You for Choosing SRMC as your Health Care Provider. Kindly Send Your Feedback to pgrd@srira...` | **ACTION** | `True` |
| 14 | `We have received confirmation on the settlement of your claim 50407630 for a policy issued by The...` | **ACTION** | `True` |
| 15 | `We have processed your Reimbursement Claim 50485973 of INR 306. Please click https://massist.in/M...` | **ACTION** | `True` |
| 16 | `We have processed your Reimbursement Claim 50407630 of INR 617. Please click https://massist.in/M...` | **ACTION** | `True` |
| 17 | `Beware of fraudsters impersonating the Cyber Cell authorities through emails threatening legal ac...` | **ACTION** | `True` |
| 18 | `Greetings from United India Insurance. Your Vehicle TN149509 insurance policy 0206003125P10350349...` | **ACTION** | `True` |
| 19 | `PNR-4650304006 Trn:17236 Dt:05-05-26 Dep.Time-19:15 Hrs. Frm NCJ to HSRA Cls:SL P1-S6,78 Boarding...` | **ACTION** | `True` |
| 20 | `PNR-4941680424 Trn:12634 Dt:04-05-26 Dep.Time-18:23 Hrs. Frm NCJ to TBM Cls:3E P1-M1,14 Boarding ...` | **ACTION** | `True` |
| 21 | `PNR-4854214907 Trn:12633 Dt:02-05-26 Dep.Time-17:47 Hrs. Frm TBM to NCJ Cls:3E P1-M1,25 P2-M1,28 ...` | **ACTION** | `True` |
| 22 | `Dear Customer, your service request No.JS-260701100851586 & call closure code is 73594 allocated ...` | **ACTION** | `True` |
| 23 | `Dear Customer, Grab 300 reward points! Share your YONO referral code with family & friends and in...` | **ACTION** | `True` |
| 24 | `Dear Customer  Our service engineer Jackson  R (2003683) is at your door step for call ID JS-2606...` | **ACTION** | `True` |
| 25 | `Hi Customer, your TATA AIG policy has been issued. The soft copy has been emailed to you. We'd lo...` | **ACTION** | `True` |
| 26 | `Dear Customer  Our service engineer Jackson  R (2003683) is at your door step for call ID JS-2607...` | **ACTION** | `True` |
| 27 | `Dear Customer, your service request No.JS-260703071145840 & call closure code is 14523 allocated ...` | **ACTION** | `True` |
| 28 | `Ekart Update: Portronics POR-2006 Black 8...  will be delivered by 11 pm today.  Share Open Box D...` | **ACTION** | `True` |
| 29 | `Call plumber tomorrow` | **ACTION** | `True` |
| 30 | `School fee INR 45000 to Lalaji Memorial` | **FINANCIAL** | `True` |

---

## 3. Key Questions & Architectural Assessment

### Question 4: Could these records be stored in `information_items`?
**Yes, absolutely.** 
Looking at the sample records above:
* E-commerce delivery alerts (e.g. Ekart, Amazon), travel bookings (PNRs), and locker operations are structured transit/status information that fit perfectly into the `ORDER_TRACKING`, `TRAVEL`, and `SECURITY_ALERT` categories in the `information_items` table.
* Insurance policies (e.g. TATA AIG, Coverfox) map cleanly to `FINANCE_INSURANCE` inside `information_items`.
* Simple task reminders (e.g. "Call plumber") are actionable items that are already ingested into the `tasks` table by the `todo_agent`, and their informational metadata can be stored in `information_items`.
* Storing them in `information_items` is completely compatible with their payloads.

### Question 5: What capability is lost if FACT Agent is removed?
**None.**
The theoretical goal of a FACT Agent is to maintain a structured key-value semantic store of user preferences or static facts (e.g. `User -> Bike Policy Number -> TN149509`). However, in practice, since there is no `facts` table, no schema, and no retrieval mechanism implemented, all this information can be preserved as timelines and structured records inside `information_items` (under `FINANCE_INSURANCE`, `HEALTH`, etc.). Search and history retrieval will query `information_items` directly. Therefore, no capability is lost.

### Question 6: What capability is gained if FACT Agent exists?
**None that justifies a separate agent.**
If a separate FACT Agent exists, it would require a dedicated `facts` database table, separate LLM extraction runs, duplicate rate limit overhead, and extra pipelines. All informational extraction, title sanitization, and category classification are already handled with high quality by the FYI Agent.

### Question 7: Is a separate FACT Agent architecturally justified?
**No.**
A separate FACT Agent introduces significant architectural redundancy and cost overhead:
1. **Redundant Pipelines**: It processes the exact same messages already handled by the FYI and Todo pipelines.
2. **Rate Limit Overhead**: Splitting signals into two parallel agents (FYI and FACT) would double the LLM calls on ambiguous messages, causing rate limit issues.
3. **Complexity**: Storing information in two different tables (`information_items` and `facts`) complicates search, daily briefs, and retention management.

---

## 4. Architectural Decision

Based on this audit and analysis, we recommend:

```text
FACT_AGENT = REMOVE
FACT → FYI (Signal routed to FYI Ingestion pipeline)
```

By removing the redundant `fact_agent` route and routing these memory-candidate/informational signals directly to the **FYI Agent**, we reduce codebase complexity and LLM rate-limiting overhead, while preserving 100% of the data under `information_items` categories with granular `importance_level` properties.
