# SECURITY.md — SNOC

> Czytać przed pierwszym kodem w sesji (reguła CLAUDE.md).

## Dane, które ta apka przetwarza (wrażliwe!)
- **telemetria żywej sieci** operatora (RRD/Cacti, LibreNMS) — read-only, nigdy nie modyfikujemy źródeł,
- **adresy instalacji i identyfikatory abonentów** (ONT↔HP↔adres) — dane osobowe w rozumieniu RODO,
- **topologia sieci** (graf, mapy) — tajemnica przedsiębiorstwa,
- decyzje/uzasadnienia operatora (AIContext) — wewnętrzne.

## Zasady
1. **Sekrety wyłącznie w `.env`** (w `.gitignore`): hasła paneli, tokeny LibreNMS, SMTP. Nigdy w kodzie/commitach/promptach.
2. **Read-only wobec źródeł**: RRD, LibreNMS, Cacti — tylko odczyt. Apka nie wykonuje ŻADNYCH akcji w sieci (żadnych SSH/SNMP-set); wyjścia to karty awarii, raporty, maile.
3. **Panel za auth** (fam_auth: hasło+2FA, rate-limit, timeout) — bind w sieci zaufanej, bez wystawiania do internetu; port 8505 za firewallem.
4. **Maile wychodzące** (fam_email): szkice do OPL wymagają zatwierdzenia człowieka — apka NIE wysyła zgłoszeń do operatorów nadrzędnych automatycznie (v1).
5. **Dane do LLM** (przyszły agent): przed wysłaniem czegokolwiek poza maszynę — anonimizacja wg praktyk z pracy mgr; lokalne modele preferowane. Decyzja per przypadek z Bartem (decisions.md).
6. **Kopie/dowody**: `data/` (rejestr, zdarzenia/evidence) zawiera dane wrażliwe — backup tylko na nośniki wewnętrzne; nie do chmur publicznych.
7. **Zależności**: rdzeń domenowy = stdlib; każda nowa paczka wymaga uzasadnienia + sprawdzenia reputacji.

## Model zagrożeń (skrót)
- największe ryzyko: **wyciek danych abonentów/topologii** przez logi, commit, prompt LLM, publiczny mostek — stąd zasady 1/5/6,
- drugie: **fałszywe alarmy → działania w terenie** — stąd polityka progów + suppression PP + confirmer ≥2 źródła przed eskalacją,
- trzecie: **utrata dowodów** (retencja RRD) — stąd evidence-freeze (nienaruszalny, patrz STOP-LISTA).
