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

## T3 — detektor jako scheduler
- [ ] serwis detektora (fam_scheduler / compose scheduler-service): przebieg co 5 min →
      MassOutage automatycznie (created_by=DETEKTOR) + evidence freeze + suppression PP + confirmer
- [ ] dedup/scalanie z T2 (odpowiednik logiki rejestru)

## T4 — panel Streamlit (strony)
- [ ] Zdarzenia: lista MassOutage + PANEL DOWODÓW (8 sekcji jak dashboard z realtime) + werdykt→AIContext
- [ ] Obserwacje/BOK: uncertain + pojedyncze zgaśnięcia + recydywy
- [ ] Zlecenia: WorkOrder dla technika (z elementem z localize i listą dotkniętych)
- [ ] Ustawienia: progi polityki z SettingsStore (debounce, coverage, baterie=50 min, impact)
- [ ] Raporty: dzienny + lead-time

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
