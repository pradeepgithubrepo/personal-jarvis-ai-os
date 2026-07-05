# Jarvis Android App — Reuse Matrix

| Component | Purpose | Current Status | Reuse Recommendation | Action |
| --- | --- | --- | --- | --- |
| `SmsRepository` | Reads and imports SMS messages incrementally | Active | Reuse | Keep |
| `JarvisNotificationListener` | Intercepts incoming third-party notifications (WhatsApp) | Active | Reuse | Keep |
| `NotificationNoiseFilter` | Normalizes texts and filters chatter | Active | Reuse | Keep |
| `SupabaseUploader` | Uploads pending signal JSON files to Supabase Storage | Active | Reuse | Keep |
| `JarvisInsightsClient` | Interfaces with the `jarvis_insights_schema` REST profile | Active | Reuse | Keep |
| `MobileSignalRepository` | Local signals Room CRUD persistence | Active | Reuse | Keep |
| `JarvisSyncWorker` | Background uploads of mobile signals | Active | Reuse | Keep |
| `InsightSyncWorker` | Background downloads of insights | Active | Reuse | Keep |
| `TodoNotificationWorker` | Periodic check and system notifications for tasks | Active | Reuse | Keep |
| `JarvisDatabase` | Room database definition and migrations | Active | Reuse | Keep |
| `AppPreferences` | App shared settings values | Active | Reuse | Keep |
| `JsonExporter` | JSON serialization helpers | Active | Reuse | Keep |
