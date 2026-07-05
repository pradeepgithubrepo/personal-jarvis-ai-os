# Jarvis V1 — Android State

> Migration Knowledge Base · Document 02  
> Produced: 2026-07-04 · Source: `ANDROID_CODEBASE_ASSESSMENT.md` + direct codebase analysis

---

## Overview

The Android application (`jarviscollector`) serves as the OS-level ingestion client and mobile companion for Jarvis AI OS. It intercepts notification streams, reads SMS databases, persists raw signals locally, and synchronises them to the central Supabase database. It also downloads downstream intelligence outputs (Todos, Financial Events, FYIs) to present to the user.

**Application package:** `com.pradeep.jarviscollector`  
**Architecture pattern:** Model-View-Repository with Room + WorkManager  
**Local database:** `jarvis_mobile.db` (Room/SQLite, schema version 3)

---

## Package Structure

| Package | Key Files | Purpose |
|---------|-----------|---------|
| `com.pradeep.jarviscollector` | `MainActivity.kt` | Central entry point, Compose state holder, permission requester, router |
| `com.pradeep.jarviscollector.database` | `JarvisDatabase.kt`, `MobileSignalDao.kt`, `InsightDaos.kt` | Room database definition and DAO accessors |
| `com.pradeep.jarviscollector.model` | `MobileSignal.kt`, `InsightEntities.kt`, `NotificationEvent.kt` | Room entities and data models |
| `com.pradeep.jarviscollector.network` | `JarvisApiClient.kt`, `JarvisInsightsClient.kt`, `SupabaseUploader.kt` | Network clients (Supabase REST + Storage) |
| `com.pradeep.jarviscollector.repository` | `MobileSignalRepository.kt`, `SmsRepository.kt`, `NotificationRepository.kt`, `TodoRepository.kt`, `FinancialRepository.kt`, `FYIRepository.kt`, `ActionsRepository.kt`, `PreferenceRepository.kt` | Data access layer |
| `com.pradeep.jarviscollector.service` | `JarvisNotificationListener.kt`, `SyncService.kt`, `JarvisSyncWorker.kt`, `InsightSyncService.kt`, `InsightSyncWorker.kt`, `TodoNotificationWorker.kt` | Background services and workers |
| `com.pradeep.jarviscollector.ui` | `HomeScreen.kt`, `TodoScreen.kt`, `FinancialScreen.kt`, `FyiScreen.kt`, `DailyBriefScreen.kt`, `FamilyScreen.kt`, `SchoolScreen.kt`, `TravelScreen.kt`, `HealthScreen.kt`, `ShoppingScreen.kt`, `NotificationScreen.kt` | Jetpack Compose screen composables |
| `com.pradeep.jarviscollector.utils` | `AppPreferences.kt`, `JsonExporter.kt`, `NotificationNoiseFilter.kt` | Utility helpers |

---

## Screens

### HomeScreen.kt

| Field | Detail |
|-------|--------|
| **Purpose** | Command center showing KPI tiles (pending todos count, financial summary, recent FYIs) |
| **Current Status** | Active |
| **Navigation Path** | Root |
| **Data Sources** | `todos`, `financial_events`, `fyi_events` Room tables |
| **Used?** | Yes |
| **Keep?** | Yes — but simplify |
| **Discard?** | No |

---

### TodoScreen.kt

| Field | Detail |
|-------|--------|
| **Purpose** | Display and toggle task items from the local cache |
| **Current Status** | Active |
| **Navigation Path** | Home → Todos |
| **Data Sources** | `TodoRepository`, `todos` Room table |
| **Used?** | Yes |
| **Keep?** | Yes |
| **Discard?** | No |

---

### FinancialScreen.kt

| Field | Detail |
|-------|--------|
| **Purpose** | View financial transactions downloaded from Supabase |
| **Current Status** | Active |
| **Navigation Path** | Home → Finance |
| **Data Sources** | `FinancialRepository`, `financial_events` Room table |
| **Used?** | Yes |
| **Keep?** | Yes — but simplify to show categories, not raw transactions |
| **Discard?** | No |

---

### FyiScreen.kt

| Field | Detail |
|-------|--------|
| **Purpose** | Display general informational updates |
| **Current Status** | Active |
| **Navigation Path** | Home → FYI |
| **Data Sources** | `FYIRepository`, `fyi_events` Room table |
| **Used?** | Yes |
| **Keep?** | Yes |
| **Discard?** | No |

---

### DailyBriefScreen.kt

| Field | Detail |
|-------|--------|
| **Purpose** | Display the synthesised daily intelligence brief |
| **Current Status** | Partial — builds static brief locally, not from server |
| **Navigation Path** | Home → Daily Brief |
| **Data Sources** | Local Room cache, `daily_briefs` table |
| **Used?** | Yes — but content is wrong |
| **Keep?** | Yes — but must be rebuilt to consume server-generated brief |
| **Discard?** | Discard the local template generation logic inside it |

**Critical Issue:** The Daily Brief screen assembles its content from a local template using Room database lookups, bypassing the LLM-generated brief on the server. This is the root cause of why the user never sees the AI-generated brief.

---

### FamilyScreen.kt

| Field | Detail |
|-------|--------|
| **Purpose** | Display family-specific updates (filtered FYI events) |
| **Current Status** | Partial — displays filtered subset of FYIs |
| **Navigation Path** | Home → Family |
| **Data Sources** | FYI events filtered by `family` category |
| **Used?** | Rarely |
| **Keep?** | Fold into FYI screen with category filter |
| **Discard?** | As a separate screen: Yes |

---

### SchoolScreen.kt

| Field | Detail |
|-------|--------|
| **Purpose** | Display school-related updates |
| **Current Status** | Partial |
| **Navigation Path** | Home → School |
| **Data Sources** | FYI events filtered by `school` category |
| **Used?** | Rarely |
| **Keep?** | Fold into FYI screen — but school events deserve dedicated priority slot in brief |
| **Discard?** | As a separate screen: Yes |

---

### TravelScreen.kt

| Field | Detail |
|-------|--------|
| **Purpose** | Display travel-related updates |
| **Current Status** | Partial |
| **Navigation Path** | Home → Travel |
| **Data Sources** | FYI events filtered by `travel` category |
| **Used?** | Rarely |
| **Keep?** | Fold into FYI screen |
| **Discard?** | As a separate screen: Yes |

---

### HealthScreen.kt

| Field | Detail |
|-------|--------|
| **Purpose** | Display health-related updates |
| **Current Status** | Partial |
| **Navigation Path** | Home → Health |
| **Data Sources** | FYI events filtered by `health` category |
| **Used?** | Rarely |
| **Keep?** | Fold into FYI screen |
| **Discard?** | As a separate screen: Yes |

---

### ShoppingScreen.kt

| Field | Detail |
|-------|--------|
| **Purpose** | Display delivery and shopping updates |
| **Current Status** | Partial |
| **Navigation Path** | Home → Shopping |
| **Data Sources** | FYI events filtered by `shopping` category |
| **Used?** | Rarely |
| **Keep?** | Fold into FYI screen |
| **Discard?** | As a separate screen: Yes |

---

### NotificationScreen.kt

| Field | Detail |
|-------|--------|
| **Purpose** | Raw ingestion logs and manual sync trigger |
| **Current Status** | Active |
| **Navigation Path** | Home → Settings / Notifications |
| **Data Sources** | `MobileSignalRepository` |
| **Used?** | Occasionally (debugging) |
| **Keep?** | Yes — as a hidden debug screen |
| **Discard?** | No — valuable for troubleshooting |

---

## Services

### JarvisNotificationListener.kt

| Field | Detail |
|-------|--------|
| **Purpose** | OS-level hook into incoming Android notifications |
| **Current Status** | Active and stable |
| **Trigger** | System-posted notification event |
| **Dependencies** | `NotificationNoiseFilter`, `MobileSignalRepository` |
| **Used?** | Yes — primary WhatsApp capture mechanism |
| **Keep?** | Yes |
| **Discard?** | No |

---

### SyncService.kt + JarvisSyncWorker.kt

| Field | Detail |
|-------|--------|
| **Purpose** | Compile un-synced local signals and POST them to Supabase Storage |
| **Current Status** | Active |
| **Trigger** | WorkManager, 3x daily (05:55, 13:55, 20:55) |
| **Dependencies** | `SupabaseUploader`, `JsonExporter` |
| **Used?** | Yes |
| **Keep?** | Yes |
| **Discard?** | No |

---

### InsightSyncService.kt + InsightSyncWorker.kt

| Field | Detail |
|-------|--------|
| **Purpose** | Pull downstream intelligence (Todos, Financial Events, FYIs) from Supabase REST API |
| **Current Status** | Active |
| **Trigger** | WorkManager, daily at 06:20 |
| **Dependencies** | `JarvisInsightsClient` |
| **Used?** | Yes |
| **Keep?** | Yes |
| **Discard?** | No |

**Note:** This worker does NOT currently pull Daily Briefs from Supabase. It pulls structured data only. Brief retrieval requires a new API endpoint on the backend.

---

### TodoNotificationWorker.kt

| Field | Detail |
|-------|--------|
| **Purpose** | Generate local Android notifications for todos due today or tomorrow |
| **Current Status** | Active |
| **Trigger** | WorkManager, 07:00 and 18:00 daily |
| **Dependencies** | `TodoNotificationHelper`, `TodoRepository` |
| **Used?** | Yes |
| **Keep?** | Yes |
| **Discard?** | No |

---

## Room Database Entities

| Entity | Table | Purpose | Status | Keep? |
|--------|-------|---------|--------|-------|
| `MobileSignal` | `mobile_signals` | Raw incoming SMS and WhatsApp captures | Active | Yes |
| `TodoEntity` | `todos` | Cache for downstream task items | Active | Yes |
| `FinancialEventEntity` | `financial_events` | Cache for financial transactions | Active | Yes |
| `FyiEventEntity` | `fyi_events` | Cache for informational alerts | Active | Yes |
| `UserPreferenceEntity` | `user_preferences` | Local settings key-value store | Active | Yes |
| `DailyBriefEntity` | `daily_briefs` | Cache for the daily brief text | Active | Yes — but must be populated from server |
| `SignalEntity` | `signals` | Stub — not used by any repository or UI | Inactive | Discard |
| `FactEntity` | `facts` | Stub — not used by any repository or UI | Inactive | Discard |
| `MerchantMappingEntity` | `merchant_mappings` | Stub — not used by any repository or UI | Inactive | Discard |
| `UserActionEntity` | `user_actions` | Stub — not used by any repository or UI | Inactive | Discard |

---

## Repositories

| Repository | Purpose | Status | Keep? |
|------------|---------|--------|-------|
| `MobileSignalRepository` | Reads/writes raw signal table | Active | Yes |
| `SmsRepository` | Queries Android SMS provider | Active | Yes |
| `NotificationRepository` | In-memory notification log for UI | Active | Yes |
| `TodoRepository` | Downstream todo cache access | Active | Yes |
| `FinancialRepository` | Downstream financial event cache | Active | Yes |
| `FYIRepository` | Downstream FYI event cache | Active | Yes |
| `PreferenceRepository` | Local settings storage | Active | Yes |
| `ActionsRepository` | Stub implementation — no functionality | Inactive | Discard |

---

## Sync Architecture

| Sync Job | Schedule | Purpose | Keep? |
|----------|----------|---------|-------|
| `JarvisSyncWorker` (signal upload) | 05:55, 13:55, 20:55 | Upload raw signals to Supabase Storage | Yes |
| `InsightSyncWorker` (insight pull) | 06:20 daily | Download todos/financial/FYI from Supabase REST | Yes |
| `TodoNotificationWorker` | 07:00 and 18:00 | Push local todo due notifications | Yes |

**Design Note:** The sync timing is deliberate. Signal upload runs at 05:55 to precede the backend morning brief job at 06:00. Insight sync runs at 06:20 to allow the backend enough time to process the uploaded signals and populate Supabase before the download occurs. This timing-based coordination is fragile and should be replaced with a proper push notification or webhook in V2.

---

## Utilities

| Utility | Purpose | Status | Keep? |
|---------|---------|--------|-------|
| `NotificationNoiseFilter` | Text-pattern rules to discard junk notifications at capture time | Active, high frequency | Yes |
| `JsonExporter` | Serialises Room records to JSON payloads for upload | Active, high frequency | Yes |
| `AppPreferences` | Shared preferences wrapper (owner name, last SMS sync time) | Active, medium frequency | Yes |

---

## Duplication Issues

1. **Category screens** (`FamilyScreen.kt`, `SchoolScreen.kt`, `TravelScreen.kt`, `HealthScreen.kt`, `ShoppingScreen.kt`): 5 nearly identical Compose layouts. Should be replaced with a single filtered list view.
2. **Worker helpers** (`JarvisSyncWorkerHelper.kt`, `InsightSyncWorkerHelper.kt`): Could be consolidated into a single orchestrator.

---

## Dead Code

| Component | Reason | Action |
|-----------|--------|--------|
| `SignalEntity` | Not used in any repository or UI | Remove |
| `FactEntity` | Not used in any repository or UI | Remove |
| `MerchantMappingEntity` | Not used in any repository or UI | Remove |
| `ActionsRepository` | Stub with no implementation | Remove |
| Local brief generation in `InsightSyncService.kt` | Conflicts with server-generated LLM brief | Remove and replace with remote brief fetch |

---

## Critical Findings

### Daily Brief End-to-End Failure

The full path from server to user screen is broken:

1. **Server generates brief** (`DailyBriefAgent`) → writes to `daily_briefs` Supabase table ✅
2. **Backend API exposes brief** → **NOT IMPLEMENTED** ❌
3. **Android fetches brief** → NOT called (no API endpoint to call) ❌
4. **Android displays brief** → displays local template instead ❌

The fix requires:
- A `GET /briefs/latest` API endpoint on the backend
- `InsightSyncWorker` to call this endpoint and store the response in the `daily_briefs` Room table
- `DailyBriefScreen` to display the stored remote brief content

### Permissions Audit

Currently requested:
- `INTERNET` — used for Supabase sync
- `READ_SMS` — used for SMS inbox scraping

Missing:
- `POST_NOTIFICATIONS` (Android 13+) — needed for WorkManager alarm display

---

## V2 Recommendations

| Component | Recommendation |
|-----------|---------------|
| HomeScreen | Keep — simplify to show brief excerpt + 3 KPI tiles |
| TodoScreen | Keep — add swipe-to-complete and snooze |
| FinancialScreen | Keep — show monthly summary cards, not raw transaction list |
| FyiScreen | Keep — add category filter inline, remove separate category screens |
| DailyBriefScreen | Rebuild — fetch from server, display as formatted card |
| FamilyScreen | Discard as separate screen — fold into FYI with filter |
| SchoolScreen | Discard as separate screen — fold into FYI with filter |
| TravelScreen | Discard as separate screen — fold into FYI with filter |
| HealthScreen | Discard as separate screen — fold into FYI with filter |
| ShoppingScreen | Discard as separate screen — fold into FYI with filter |
| NotificationScreen | Keep as hidden debug screen |
| Voice Capture | Add as new screen — microphone button, transcription, submit to Jarvis |

---

*Document: 02_ANDROID_STATE.md*  
*Part of Jarvis V1 Migration Knowledge Base*
