# Jarvis Android App — Removal Candidates

The following table lists components and files in the Android codebase that are recommended for removal, consolidation, or refactoring.

| Component | Category | Current Status | Recommended Action | Justification |
| --- | --- | --- | --- | --- |
| **Local Daily Brief Generator** (Inside `InsightSyncService.kt`) | Local Business Logic | Active | Remove | Generates a static template-based brief locally on the device from local database states. This conflicts with the central architectural pipeline where morning/evening briefs are compiled by the production LLM (`qwen2.5:1.5b`) and saved in Supabase. The Android app should instead fetch the `daily_briefs` table directly. |
| **`SignalEntity`** | Model | Obsolete | Remove | Room entity mapping class. Unused by any database repository, sync worker, or presentation layer. |
| **`FactEntity`** | Model | Obsolete | Remove | Room entity mapping class. Unused by any database repository, sync worker, or presentation layer. |
| **`MerchantMappingEntity`** | Model | Obsolete | Remove | Room entity mapping class. Unused by any database repository, sync worker, or presentation layer. |
| **`ActionsRepository`** | Repository | Obsolete | Remove | Stub repository that is never consumed by the UI layer. |
| **`FamilyScreen.kt`, `SchoolScreen.kt`, `TravelScreen.kt`, `HealthScreen.kt`, `ShoppingScreen.kt`** | UI Screens | Duplicated | Consolidate | These 5 screens are duplicate implementations of a generic FYI list filtered by category. They should be consolidated into a single reusable `FyiCategoryListScreen` parameterised by category name and color scheme. |
