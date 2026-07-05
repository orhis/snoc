# session-history — SNOC

## 2026-07-05 (założenie projektu)
- Decyzje: nazwa SNOC, rygor pełny, port 8505 (Bart via pytania).
- Kontekst: SOSDH upadł biznesowo → kanibalizacja schematu tickets; FAM = obudowa; rdzeń = realtime/ (zwalidowany).
- Zrobione: scaffold + fundament docs. Następne: T0 dokończenie (venv+smoke), potem T1 (transplantacja rdzenia).

## 2026-07-05 (b) — T0 dokończenie + T1
- T0: venv **Python 3.13** (fam_* wymaga ≥3.11!), pip z tagu v0.3.0, bootstrap admin, panel HTTP 200, push do github.com/orhis/snoc.
- T1: rdzeń przeniesiony (core_gpon, importy względne, paths.py SNOC_*), artefakty w data/ (D7), 9 testów passed (w tym regresja goldów), pipeline smoke = wyniki 1:1 z realtime.
- Następne: T2 (modele MassOutage/AIContext/WorkOrder w SQLite) → potem T3 scheduler / T4 panel.
