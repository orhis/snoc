# TODO — SNOC (wątki; 1 wątek = 1 branch)

## T0 — fundament projektu ✅ UKOŃCZONE (2026-07-05)
- [x] scaffold `fam-new` (port 8505, moduły email/audit/scheduler)
- [x] CLAUDE.md (rygor) + SECURITY.md + docs/
- [x] FAM.md (poziom D) + wpis w FAM/INTEGRACJA.md
- [x] git init + pierwszy commit + push → github.com/orhis/snoc (main)
- [x] venv (**Python 3.13** — fam_* wymaga ≥3.11, systemowy 3.10 za stary!) + pip install
      + bootstrap admina (`admin`) + smoke: panel HTTP 200 na :8505 ✅

## T1 — transplantacja rdzenia domenowego (z `F:\BRT\...\realtime\`)
- [ ] `app/core_gpon/`: rrd_los, topo_localize, c_detect, c_diagnose, c_confirm, c_evidence, pp_suppression
      (bez zmian logiki; config → `app/settings.py` Settings)
- [ ] artefakty → `data/topo/` (topo_repaired: nodes/edges/hp_to_slupek/ont_to_hp + ont_uzupelnione_net47)
      + `data/klucz/`, `data/pp/`, `data/eventlog/`
- [ ] testy: przenieść walidacje (self-testy localize, regresja goldów jako testy z zamrożonych dowodów)

## T2 — modele SQLite wg schematu SOSDH (bez multi-tenant) [D2] ✅ UKOŃCZONE (2026-07-05)
- [x] `MassOutage` + `AIContext` (reasoning WYMAGANY, snapshot z chwili decyzji) + `WorkOrder` w app/models.py
- [x] `app/services/registry_service.py` — register() kontrakt jak c_registry (scalanie olts+start±1h,
      werdykty nietykalne, recydywa globalnie, JSONL dowodów zostaje plikowo D6) + add_verdict()
- [x] pipeline: wstrzyknięcie rejestru (registry=) — rdzeń core_gpon czysty (D3), app podaje DB
- [x] testy +4 (idempotencja/scalanie-po-re-diagnozie/recydywa/reasoning-wymagany) — **13 passed łącznie**
- [x] smoke E2E: pipeline→DB = 7 kart MassOutage, recydywa S/017 0→1→2, B06 start z 5-min (0930)
- [x] migracja CSV: NIEPOTRZEBNA — rejestr odtwarza się z pulla; stary CSV realtime = archiwum
- [ ] drobne: DeprecationWarning utcfromtimestamp (Py3.13) — do T3/T4 (uwaga aware-vs-naive!)

## T3 — detektor jako scheduler ✅ UKOŃCZONE (2026-07-05)
- [x] `app/scheduler.py` — pętla co SNOC_SCAN_INTERVAL (300 s), pipeline→registry_service (DB),
      błąd przebiegu nie zabija pętli; compose już woła `python -m app.scheduler`
- [x] progi polityki ze SettingsStore nakładane PRZED każdym przebiegiem (`services/policy.py`)
- [x] dedup/scalanie = registry_service (T2); testy +2 (policy defaults/override, iteracja→DB)

## T4 — panel Streamlit (strony) ✅ v1 UKOŃCZONE (2026-07-05)
- [x] nawigacja (st.navigation, gate logowania w jednym miejscu) + layout wide
- [x] **Zdarzenia**: karty z DB, panel dowodów 9 sekcji (sygnatura/zakres/mapa+coverage po ludzku/
      PP-live z ID okien/confirmer/diagnoza/rekomendacja/werdykt/dowody), werdykt→AIContext
      (reasoning wymagany), zmiana statusu, „Zlecenie dla technika" jednym przyciskiem
- [x] **Obserwacje**: uncertain + recydywy elementów
- [x] **Zlecenia**: WorkOrder (status/typ/przypisanie/notatki z terenu)
- [x] **Ustawienia**: progi D5 ze SettingsStore (admin-only; scheduler stosuje ≤5 min)
- [ ] Raporty (dzienny+lead-time jako strona) — v2; ⚠ przejście klikowe przez Barta = realny UAT
- [ ] BOK-log (pojedyncze zgaśnięcia) nie trafia do DB — tylko log pipeline; do rozważenia w v2

## T5 — powiadomienia (fam_email)
- [ ] mail przy nowej MassOutage (klasa+zakres+rekomendacja+link do panelu)
- [ ] szkic maila do OPL (wzor_mail_OPL) przy podtypie brak_ostrzezenia_silowni — do zatwierdzenia, NIE auto-send
- [ ] ⚠ wymaga od Barta: tabela ID łączy OPL per lokalizacja

## T6 — deploy Synology
- [ ] compose web+scheduler (jest z fam-new --with-scheduler) + mount RRD + .env produkcyjny
- [ ] decyzja Barta: mount rra/ z serwera Cacti na Synology vs apka na serwerze Cacti

## Backlog (z realtime/README — nadal aktualne)
- [ ] pokrycie 12/12 OLT (W02/W03/W11/W12 bez danych ONT w pullu)
- [ ] LibreNMS live API jako confirmer/early-warning (sensory voltage → lead ~2h dla power)
- [ ] suppression PP z lokalizacją (parsować body .msg)
- [ ] agent AI (KONCEPCJA_AGENT_WORKFLOW_DANE.md; decyzja: Bielik lokalnie vs API)
- [ ] weryfikacja karty gpon_1/2 pleszewa świeżym pullem (44 ONT z dedukcji)
- [ ] przegląd 29 długich mostków w QGIS (Bart, warstwa mostki_do_weryfikacji.shp)
