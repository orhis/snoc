# CLAUDE.md — SNOC (SuperNET NOC)

> Czytaj na starcie KAŻDEJ sesji, w całości. Rygor: **PEŁNY** (poważna/produkcyjna/duża apka).
> Standard pracy: FAM/WORKFLOW.md. ⚠️ To apka produkcyjna (docelowo nadzór żywej sieci) — ostrożność > tempo.

## 0. Bieżący stan (wygrywa przy sprzeczności)
> Aktualizowane świadomie na koniec sesji. Gdy reszta pliku jest sprzeczna — **obowiązuje ta sekcja**.
2026-07-05: scaffold z `fam-new` (port 8505, moduły: email, audit, scheduler) + fundament docs.
Rdzeń domenowy (detekcja/diagnoza GPON) JESZCZE NIE przeniesiony z `F:\BRT\00.Informatyka_II_stopień\realtime\`
— plan transplantacji w `docs/TODO.md`. Priorytet #1: wątek T1 (rdzeń core_gpon + testy przechodzą).

## Cel i zakres
**SNOC = wewnętrzny system NOC dla SuperNET/RCI**: automatycznie wykrywa awarie GPON z telemetrii
(RRD/Cacti, LibreNMS), lokalizuje je na grafie topologii (naprawiony graf z QGIS), klasyfikuje
(drzewo decyzyjne, polityka Barta: debounce 5/10 min, 1 ONT=BOK, klaster≥2+coverage), prowadzi
karty awarii wg schematu przeszczepionego z SOSDH (**MassOutage/AIContext/WorkOrder — BEZ multi-tenant**),
zbiera decyzje operatora z uzasadnieniem (gold-data pod przyszłego agenta AI), panel Streamlit,
deploy Docker/Synology.
**Czym NIE jest:** platformą hurtową OSD↔OK (to upadło z SOSDH) · systemem billingowym · zamiennikiem
LibreNMS/Cacti (czyta z nich, nic w nich nie zmienia).
**Pochodzenie rdzenia:** `realtime\` (kontener C przy pracy mgr) — moduły zwalidowane na 4 realnych
zdarzeniach (gold 4-OLT Orange 26.05, testy kontrolowane E03 29.05, power węzła B06 02.06, prąd-obszar 30.05).

## Tryb pracy (ping-pong)
- Jeden krok / jedno pytanie na raz → pokaż wynik → **CZEKAJ na OK**. Plan przed akcją dla ≥2 kroków (najpierw całość, akceptacja, potem krok po kroku).
- Wybór techniczny: **2–3 opcje** (zyski / straty / rekomendacja + dlaczego). Decyzje wspólnie, nie za mnie.
- **Specjalista techniczny i architekt, nie maszyna do kodu.** Rozumienie > szybkość: kod, którego nie rozumiem, nie będzie utrzymany.
- **Krytyka bez potakiwania** — mów „nie" z uzasadnieniem; nie broń pomysłu bo Twój; pytaj „dlaczego?" zanim zmienisz coś ustalonego. „stop/nie tak/czekaj" = przerwij i dopytaj.
- Konsultuję z innym LLM — odnieś się merytorycznie, nie obronnie.

## Komendy
- **„zapisz wszystko / zapisz pracę"** (pełny rytuał, w kolejności):
  1. `docs/changelog.md` — wpis pod datą (`- {moduł}: {co}`),
  2. `docs/TODO.md` — `[x]` zamknięte + nowe,
  3. `docs/decisions.md` — nowe decyzje (numerowane),
  4. sekcja **§0** tego pliku — nadpisz „bieżący stan",
  5. `docs/session-history.md` — wpis `## YYYY-MM-DD` (koniec sesji),
  6. `git status` → **commit lokalny** (`feat/fix/chore(scope): co`) → **push TYLKO na potwierdzenie**.
  - Zasada: *brak wpisu = praca nie zamknięta; „ukończone" bez wpisu = nieprawda.*
- **„zapisz do todo"** = tylko `TODO` + `decisions`, **bez commitu**.

## Twarde NIGDY / ZAWSZE
**NIGDY:** sekrety w repo/promptach/kodzie (tylko `.env`/`secrets.toml` w `.gitignore`) · commit/push bez prośby · `--no-verify` · zmiana architektury/decyzji bez dyskusji · nowa technologia bez zgody · `eval`/`exec`/`shell=True`/`pickle.loads`/`verify=False` · działania na produkcji/danych wrażliwych bez zgody · sugerowanie OVERRIDE jako obejścia trudności.
**ZAWSZE:** czytaj `CLAUDE.md` + `SECURITY.md` **przed pierwszym kodem w sesji** · testy przed commitem · weryfikuj nową paczkę (CVE/reputacja) · cytuj numer decyzji przy zmianie funkcji · output LLM = Zero Trust (waliduj, nie wykonuj ślepo).

## OVERRIDE (świadome złamanie zasady — tylko ja)
```
OVERRIDE: [zasada]
Powód: [dlaczego w tym przypadku]
Zakres: [jedna operacja / plik / sesja — NIE „na zawsze"]
```
Bez tych trzech — brak OVERRIDE. Ty nigdy nie proponujesz; gdy zasada blokuje → zatrzymaj się i powiedz.

## Anty-regresja — refactor checklist (przy zmianie sygnatury/funkcji/modelu)
- [ ] `grep` starych callsite'ów + martwego kodu (stary parametr/pole = ryzyko + chaos).
- [ ] docstringi/komentarze opisujące stary mechanizm — zaktualizuj.
- [ ] nowy wyjątek → czy handler w UI (inaczej traceback z danymi wrażliwymi)?
- [ ] nowe pole w modelu → mirror w migracji/upsert (brak = ciche zepsucie w testach).
- [ ] nowa funkcja w service → ma callera? (bez = dead code).
- [ ] `pytest -x` zielone.
- Łap **konkretne wyjątki**, nie `except Exception`.

## STOP-LISTA / known-traps (czego NIE robić — czytane co sesję)
> Gdy Bart powie „tego nie rób" ALBO naprawimy powtarzalną pułapkę — **wpisz tu**.
- **Nie buduj obudowy ad-hoc** (własny auth/config/serwer), gdy FAM ma moduł — incydent 2026-07-04 w realtime/.
- **RRD:** timestamp slotu = KONIEC interwału; czasy komunikatora/eventlogu = LOKALNE (CEST/CET), RRD = UTC — zawsze konwertuj świadomie (błąd D8 kosztował „niewidzialne" testy E03).
- **Evidence freeze jest nienaruszalny** — raz zamrożonych dowodów zdarzenia nie nadpisujemy (retencja RRD!).
- **Rejestr/dowody:** poza zakresem źródła = `no_coverage`, NIGDY „brak zdarzenia".
- **Streamlit:** key widgetu/formularza NIE może równać się kluczowi session_state, który potem nadpisujesz (kolizja → StreamlitAPIException). Smoke HTTP ≠ UAT — flow UI testuj AppTestem.
- **Nazwa ONU-a:b z net47** nie zawiera OLT ani karty — pełny adres ONT = (OLT, karta, port, indeks).

## Mapa dokumentów
**Rdzeń (czytaj):** CLAUDE.md (§0!) · SECURITY.md (przed kodem) · docs/session-history.md (wznowienie) · docs/TODO.md · docs/dla-rewidenta.md (jeden, aktualny, samodzielny).
**Duży projekt — dodatkowo:** docs/decisions.md (log DLACZEGO, numerowane) · docs/SLOWNIK.md (terminy domenowe GPON/NOC — powstanie przy T1).
> Anty-przerost: jeden aktualny plik dla rewidenta (kasuj stare wersje). Aktualizacja CLAUDE.md = jawna czynność, nie side-effect.

## Handoff (na starcie sesji)
1. CLAUDE.md (cały, zwłaszcza §0 i STOP-LISTA) → 2. SECURITY.md → 3. docs/session-history.md (1–2 ostatnie) → 4. docs/TODO.md Open → 5. `git log --oneline -10`.

## FAM (poziom D)
Apka stoi na skeletonie FAM (patrz `FAM.md`). Przed pisaniem od zera auth/maili/DB/Dockera —
sprawdź moduły FAM. Ulepszenie obszaru modułowego = **backport do FAM** (test, bump, CHANGELOG;
SECURITY: gdy bezpieczeństwo). Logika domenowa GPON (detekcja/diagnoza/topologia) = **NIE do FAM**
(reguła INTEGRACJA.md).
