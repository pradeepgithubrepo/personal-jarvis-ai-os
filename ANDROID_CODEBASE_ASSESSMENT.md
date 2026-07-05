# Android Codebase Assessment Report

This document serves as the baseline technical audit and architecture baseline of the existing Jarvis Android application ("Jarvis Collector"). 

---

## SECTION 1 - Executive Summary

### 1. Application Purpose
The Jarvis Android app acts as the OS-level ingestion client and mobile companion for the Jarvis AI OS. It intercepts notification streams (WhatsApp/WhatsApp Business), reads SMS message databases, persists raw signals locally, and synchronises them to the central Supabase database. It also downloads downstream intelligence outputs (Todos, Financial transactions, and FYI events) to present to the user.

### 2. Current Maturity Level
- **Signal Ingestion**: Highly stable. Automatic background capture of incoming WhatsApp notifications and SMS messages is fully implemented.
- **Sync Engine**: Working. Employs background WorkManager jobs mapped to the central pipeline schedule.
- **Presentation Layer**: Functional but simple Compose UI layouts. The Daily Brief is static/template-based and generated locally, representing a mismatch with the production LLM pipeline.

### 3. Major Capabilities Implemented
- Local Room DB storage for raw incoming signals.
- In-memory notification capture and noise filtering.
- OkHttp/REST integration with Supabase storage buckets and tables.
- Daily brief local template building.

### 5. Overall Architectural Assessment
The architecture follows a standard Model-View-Repository pattern with Room and WorkManager. The codebase conforms to the presentation-only rule, though the template-based Daily Brief generator represents a minor violation of the "No local business logic duplication" rule.

---

## SECTION 2 - Package Structure

- **`com.pradeep.jarviscollector`**:
  - `MainActivity.kt`: Central entry point, Compose state holder, permission requester, and router.
- **`com.pradeep.jarviscollector.database`**:
  - `JarvisDatabase.kt`: Main Room Database definition listing entities and DAO accessors.
  - `MobileSignalDao.kt`: Data Access Object for local signals.
  - `InsightDaos.kt`: DAO definitions for Todos, Financial Events, FYIs, Preferences, and Briefs.
- **`com.pradeep.jarviscollector.model`**:
  - `MobileSignal.kt`: Main schema mapping for raw SQLite mobile signals.
  - `NotificationEvent.kt`: Simple in-memory notification message carrier.
  - `InsightEntities.kt`: Room entities for downstream tables (`todos`, `financial_events`, `fyi_events`, `user_preferences`, `user_actions`, `signals`, `facts`, `merchant_mappings`, `daily_briefs`).
- **`com.pradeep.jarviscollector.network`**:
  - `JarvisApiClient.kt`: Interface and OkHttp client for network requests.
  - `JarvisInsightsClient.kt`: Direct Postgrest REST client mapping queries to `jarvis_insights_schema`.
  - `SupabaseUploader.kt`: OkHttp multipart file-uploader for JSON logs.
- **`com.pradeep.jarviscollector.repository`**:
  - `MobileSignalRepository.kt`, `SmsRepository.kt`, `NotificationRepository.kt`: Capture/persistence wrappers.
  - `TodoRepository.kt`, `FinancialRepository.kt`, `FYIRepository.kt`, `ActionsRepository.kt`, `PreferenceRepository.kt`: Accessors mapping local cache tables to UI composables.
- **`com.pradeep.jarviscollector.service`**:
  - `JarvisNotificationListener.kt`: OS-level notification binder.
  - `SyncService.kt` / `JarvisSyncWorker.kt` / `JarvisSyncWorkerHelper.kt`: Ingest and upload pipeline.
  - `InsightSyncService.kt` / `InsightSyncWorker.kt` / `InsightSyncWorkerHelper.kt`: Downstream sync pipeline.
  - `TodoNotificationWorker.kt` / `TodoNotificationHelper.kt`: Local notification generators.
- **`com.pradeep.jarviscollector.ui`**:
  - Composable files representing each user dashboard screen: `HomeScreen.kt`, `TodoScreen.kt`, `FinancialScreen.kt`, `FyiScreen.kt`, `DailyBriefScreen.kt`, `FamilyScreen.kt`, `SchoolScreen.kt`, `TravelScreen.kt`, `HealthScreen.kt`, `ShoppingScreen.kt`, `NotificationScreen.kt`.
- **`com.pradeep.jarviscollector.utils`**:
  - `AppPreferences.kt`: Shared preferences wrapper.
  - `JsonExporter.kt`: JSON serialisation helpers.
  - `NotificationNoiseFilter.kt`: Text matching filters.

---

## SECTION 3 - Screens Inventory

| Screen Name | Purpose | Status | Navigation Path | Data Sources |
| --- | --- | --- | --- | --- |
| **HomeScreen** | Command Center & KPI Tiles | `ACTIVE` | Root | `todos`, `financial_events`, `fyi_events` |
| **TodoScreen** | Display and toggle task items | `ACTIVE` | Home -> Todos | `TodoRepository` / `todos` table |
| **FinancialScreen**| View transactions | `ACTIVE` | Home -> Finance | `FinancialRepository` / `financial_events` |
| **FyiScreen** | Display general updates | `ACTIVE` | Home -> FYI | `FYIRepository` / `fyi_events` |
| **DailyBriefScreen**| Displays synthesis text | `PARTIAL` | Home -> Daily Brief | Local daily brief Room cache |
| **FamilyScreen** | Family-specific updates | `PARTIAL` | Home -> Family | FYI events filtered by family category |
| **SchoolScreen** | School updates | `PARTIAL` | Home -> School | FYI events filtered by school category |
| **TravelScreen** | Travel updates | `PARTIAL` | Home -> Travel | FYI events filtered by travel category |
| **HealthScreen** | Health updates | `PARTIAL` | Home -> Health | FYI events filtered by health category |
| **ShoppingScreen** | Delivery updates | `PARTIAL` | Home -> Shopping | FYI events filtered by shopping category |
| **NotificationScreen**| Raw ingestion logs & manual sync | `ACTIVE` | Home -> Settings | `MobileSignalRepository` |

---

## SECTION 4 - Services Inventory

- **`JarvisNotificationListener`** (NotificationListenerService)
  - *Purpose*: Hooks into incoming notifications on Android.
  - *Trigger*: System posted notification event.
  - *Dependencies*: `NotificationNoiseFilter`, `MobileSignalRepository`.
  - *Status*: `KEEP`
- **`SyncService`**
  - *Purpose*: Compiles un-synced local signals and posts them to Supabase Storage.
  - *Trigger*: Worker trigger or Manual UI click.
  - *Dependencies*: `SupabaseUploader`, `JsonExporter`.
  - *Status*: `KEEP`
- **`InsightSyncService`**
  - *Purpose*: Pulls tables from Supabase REST schema.
  - *Trigger*: Worker trigger or Manual UI click.
  - *Dependencies*: `JarvisInsightsClient`.
  - *Status*: `KEEP`

---

## SECTION 5 - Data Collection Layer

- **SMS Collection**:
  - *Mechanism*: Queries `Telephony.Sms.Inbox.CONTENT_URI` for inbox logs.
  - *Status*: Active.
  - *Reliability*: High. Restricted to read permissions.
- **Notification Collection**:
  - *Mechanism*: Binds `NotificationListenerService` looking for WhatsApp notification packages (`com.whatsapp`, `com.whatsapp.w4b`).
  - *Status*: Active.
  - *Reliability*: High (requires OS notification access approval).

---

## SECTION 6 - Room Database Assessment

Database Name: `jarvis_mobile.db`
Current Schema Version: `3`

### Entities
1. `mobile_signals` (ID: Int auto-increment) - Stores raw local SMS and WhatsApp captures.
2. `todos` (todo_id: String PK) - Cache for downstream tasks.
3. `financial_events` (financial_event_id: String PK) - Cache for downstream transactions.
4. `fyi_events` (fyi_event_id: String PK) - Cache for alerts.
5. `user_preferences` (preference_key: String PK) - Cache for system variables.
6. `daily_briefs` (id: String PK) - Cache for current brief text.
7. `facts`, `signals`, `merchant_mappings`, `user_actions` - Inactive/stub entity classes.

---

## SECTION 7 - Supabase Integration Assessment

- **SupabaseUploader**: Posts JSON text blobs containing pending raw signals directly to Supabase storage bucket `jarvis-signals` under `/incoming`.
- **JarvisInsightsClient**: Interfaces with the `jarvis_insights_schema` REST profile. Sends GET requests to pull changes and PATCH/POST updates.
- **Auth model**: Uses the project wide Bearer `ANON_KEY` / `API_KEY` defined in `BuildConfig`.

---

## SECTION 8 - Sync Architecture

- **JarvisSyncWorker** (Signal Upload):
  - *Schedule*: 3 times daily (05:55 AM, 01:55 PM, 08:55 PM) to precede the python cron schedules.
  - *Triggers*: Network connectivity constraints.
- **InsightSyncWorker** (Downstream Pull):
  - *Schedule*: Daily at 06:20 AM.
  - *Triggers*: Network connectivity constraints.
- **TodoNotificationWorker**:
  - *Schedule*: Runs twice daily (07:00 AM, 06:00 PM).
  - *Purpose*: Triggers local system notifications for tasks due today or tomorrow.

---

## SECTION 9 - Repository Inventory

1. `MobileSignalRepository` (Active) - Reads/Writes raw signal table.
2. `SmsRepository` (Active) - Queries Android providers.
3. `NotificationRepository` (Active) - UI log memory list.
4. `TodoRepository`, `FinancialRepository`, `FYIRepository` (Active) - Downstream tables cache.
5. `PreferenceRepository`, `ActionsRepository` (Partial) - Settings storage mapping.

---

## SECTION 10 - Utilities Assessment

- **`JsonExporter`**: High frequency usage. Used to serialise Room records to JSON payloads.
- **`NotificationNoiseFilter`**: High frequency usage. Cleans junk notifications.
- **`AppPreferences`**: Medium frequency usage. Handles local preferences (owner name, last SMS sync time).

---

## SECTION 11 - Notification Architecture

- **Channels**: Standard channels registered (`todo_reminders` with High Importance for urgent tasks).
- **Listeners**: OS NotificationListenerService bindings intercepts third-party chat messages.
- **Generation**: Triggered in background via `TodoNotificationWorker` when matching tasks are due.

---

## SECTION 12 - Permissions Assessment

- **Requested**:
  - `android.permission.INTERNET` (Used for Supabase sync).
  - `android.permission.READ_SMS` (Used for SMS inbox scraping).
- **Unused**: None.
- **Recommendation**: Request `android.permission.POST_NOTIFICATIONS` for Android 13+ to ensure WorkManager alarms display correctly.

---

## SECTION 13 - Test Asset Assessment

- `ExampleUnitTest.kt` (Obsolete/Boilerplate) - Standard empty test file.
- `ExampleInstrumentedTest.kt` (Obsolete/Boilerplate) - Standard instrumented placeholder.

---

## SECTION 14 - Dead Code Analysis

- **`com.pradeep.jarviscollector.model.SignalEntity`** - Not used in any repository or UI.
- **`com.pradeep.jarviscollector.model.FactEntity`** - Not used in any repository or UI.
- **`com.pradeep.jarviscollector.model.MerchantMappingEntity`** - Not used in any repository or UI.
- **`com.pradeep.jarviscollector.repository.ActionsRepository`** - Stub implementation.

---

## SECTION 15 - Duplication Analysis

- **Category screens** (`FamilyScreen.kt`, `SchoolScreen.kt`, `TravelScreen.kt`, `HealthScreen.kt`, `ShoppingScreen.kt`): These 5 Compose screen layouts are near-identical, copying list rendering structures with minor color changes.
- **Worker Helpers**: `JarvisSyncWorkerHelper` and `InsightSyncWorkerHelper` could be consolidated into a single orchestrator service.

---

## SECTION 16 - Reuse Assessment

### ASSETS TO PRESERVE
- **SMS ingestion**: `SmsRepository` is fully optimized for incremental queries.
- **Notification interceptor**: `JarvisNotificationListener` and `NotificationNoiseFilter` correctly ignore system clutter.
- **Supabase Integration**: OkHttp REST profile integrations are highly robust.

---

## SECTION 17 - Removal Candidates

### REMOVAL CANDIDATES
- **Local Daily Brief Generator** (Inside `InsightSyncService.kt`): Generates static briefs locally from database lookups, conflicting with the LLM-compiled morning briefs inside Supabase. Recommendation: Replace with direct download of remote brief content.
- **Unused Entities**: `SignalEntity`, `FactEntity`, and `MerchantMappingEntity` should be pruned to keep the Room schema clean.

---

## SECTION 18 - Android Modernization Readiness

- **Home Dashboard**: Reusable as is. Ready to show active tiles.
- **Daily Brief**: Needs update to download LLM briefs directly from the `daily_briefs` table instead of assembling static text locally.
- **Todo/FYI/Finance**: Full backend sync is operational. Compose views can be easily modernized to follow the streamlined glassmorphic design layout.
