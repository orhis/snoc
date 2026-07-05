# TODO — SNOC (wątki; 1 wątek = 1 branch)

## T0 — fundament projektu ⬅ W TOKU (2026-07-05)
- [x] scaffold `fam-new` (port 8505, moduły email/audit/scheduler)
- [x] CLAUDE.md (rygor) + SECURITY.md + docs/
- [x] FAM.md (poziom D) + wpis w FAM/INTEGRACJA.md
- [ ] git init + pierwszy commit (na „zapisz wszystko")
- [ ] venv + `pip install -r requirements.txt` + bootstrap admina + smoke `streamlit run`

## T1 — transplantacja rdzenia domenowego (z `F:\BRT\...\realtime\`)
- [ ] `app/core_gpon/`: rrd_los, topo_localize, c_detect, c_diagnose, c_confirm, c_evidence, pp_suppression
      (bez zmian logiki; config → `app/settings.py` Settings)
- [ ] artefakty → `data/topo/` (topo_repaired: nodes/edges/hp_to_slupek/ont_to_hp + ont_uzupelnione_net47)
      + `data/klucz/`, `data/pp/`, `data/eventlog/`
- [ ] testy: przenieść walidacje (self-testy localize, regresja goldów jako testy z zamrożonych dowodów)

## T2 — modele SQLite wg schematu SOSDH (bez multi-tenant) [D2]
- [ ] `MassOutage` (tytuł, opis, obszar, started_at [u nas: z DETEKCJI, nie zgłoszenia] + override+powód,
      ended_at, status, created_by[user/DETEKTOR]) — zastępuje incident_registry.csv
- [ ] `AIContext` (FK→MassOutage/WorkOrder, action_type, input_snapshot JSON=model dowodów,
      decision, reasoning WYMAGANE, time_to_decision, confidence, was_overridden+kto+czemu)
- [ ] `WorkOrder` (numer, typ[serwis/wizja/budowa/nadzór], status-workflow, FK→MassOutage,
      terminy, miejsce [element z localize!], notatki, assigned_to)
- [ ] migracja: obecny incident_registry.csv/jsonl → MassOutage+AIContext (dane z walidacji zostają)

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
