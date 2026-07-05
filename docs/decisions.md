# decisions.md — SNOC (log DLACZEGO, numerowane)

**D1 (2026-07-05): Nowa apka na FAM, poziom D** — zamiast (a) rozwijać ad-hoc pakiet w `realtime/`
(incydent: zbudowana własna obudowa dublująca FAM) i (b) reanimować SOSDH (Django+Postgres+Redis —
temat biznesowo upadł, za ciężki dla jednego operatora). FAM daje przetestowane auth/2FA, config_db,
deploy Synology, email, scheduler, audit. Nazwa: **SNOC**, port **8505**, rygor CLAUDE.md: **pełny**.

**D2 (2026-07-05): Schemat kart awarii przeszczepiony z SOSDH, bez multi-tenant** —
MassOutage (kontener awarii; u nas tworzony AUTOMATYCZNIE przez detektor, started_at=czas
wykrycia w danych, nie pierwszego telefonu) + AIContext (każda decyzja operatora z input_snapshot
+ decision + WYMAGANYM reasoning = gold-data pod agenta v1→v1.5→v2) + WorkOrder (zlecenie dla
technika z elementem wskazanym przez localize). Wyrzucone: network/contract FK, pricing, role
per sieć. SOSDH pozostaje skarbnicą wzorców, nie runtime.

**D3 (2026-07-05): Rdzeń domenowy GPON przenoszony bez zmian logiki i NIE do FAM** —
moduły z `realtime/` (detekcja/lokalizacja/diagnoza/dowody) są zwalidowane na 4 realnych
zdarzeniach; zmiany tylko adaptacyjne (config→Settings). Reguła INTEGRACJA.md: „klasyfikator
GPON nie do FAM" — zostaje w apce jako `app/core_gpon/`.

**D4 (2026-07-05): Topologia zostaje plikowa (artefakt `data/topo/`)** — naprawiony graf
z QGIS (CRS-fix, spina 99,9%, ONT→HP 96%) jest świeższy niż import w SOSDH-PostGIS; baza
przestrzenna = ewentualnie później, gdy zajdzie potrzeba edycji topologii z UI. Aktualizacja
artefaktu = re-build na laptopie (topo_repair.py + build_spine.py) i podmiana folderu.

**D5 (2026-07-05): Polityka detekcji (decyzje operatorskie Barta, przeniesione z realtime):**
debounce 5/10 min; 1 ONT = BOK (bez alarmu); klaster ≥2 fresh w tym samym oknie + blisko
topologicznie (coverage ≥0.5; przy małej saturacji 2/2=mocny sygnał); baterie siłowni = 50 min
(dłużej → weryfikacja rachunków + komunikaty Enea + agregat); brak ostrzeżenia siłowni przy
padzie węzła → po 10 min szkic maila do OPL; wielkie miasto w adresie klienta (Warszawa/Poznań)
= billing spoza obszaru, odrzucać. Progi edytowalne w SettingsStore (T4).

**D6 (2026-07-05): Evidence freeze nienaruszalny** — dowody zdarzenia (wycinki RRD ±2h, oba RRA)
zapisywane raz przy wykryciu, nigdy nie nadpisywane (retencja 5-min = 50 h; spory z OPL trwają
tygodnie). Poza zakresem źródła = `no_coverage`, nigdy „brak zdarzenia".
