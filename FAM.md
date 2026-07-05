# FAM.md — SNOC

**Poziom integracji: D (pełny fundament — nowa apka na skeletonie FAM).**

| obszar | źródło |
|---|---|
| auth (hasło+2FA, rate-limit, timeout) | fam_auth (skeleton) |
| baza/config/settings | fam_config_db (skeleton) |
| Docker/compose (web+scheduler) | fam_deploy (wygenerowane) |
| maile | fam_email (wired w app/integrations.py) |
| audit | fam_audit (wired) |
| scheduler | fam_scheduler (wired) |

**Domenowe (NIE do FAM):** app/core_gpon/ — detekcja/lokalizacja/diagnoza GPON, topologia, evidence.
**Backport-kandydaci (jak dojrzeją):** evidence-freeze jako wzorzec, model AIContext-lite.
