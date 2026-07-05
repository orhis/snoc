# changelog — SNOC

## 2026-07-05
- projekt: scaffold fam-new (port 8505, moduły email/audit/scheduler)
- docs: CLAUDE.md (rygor) + SECURITY.md + TODO (wątki T0–T6) + decisions D1–D6
- core_gpon: transplantacja rdzenia z realtime/ (8 modułów + paths + pipeline), testy 9 passed, smoke OK (T1)
- data/: artefakty topo/klucz/pp/eventlog (gitignored, D7) + README
- models+services: MassOutage/AIContext/WorkOrder + registry_service (DB), pipeline DI, testy 13 passed (T2)
- scheduler+policy: serwis 5-min z progami ze SettingsStore (T3); panel: 4 widoki + werdykty + zlecenia (T4 v1); testy 15 passed
