# -*- coding: utf-8 -*-
"""
c_confirm — confirmer LibreNMS eventlog (teza multi-source: ≥2 źródła przed eskalacją).
Dla zdarzenia z c_diagnose sprawdza w eventlogu "Device status changed to Down/Up"
dla urządzeń danej lokalizacji (sysName→OLT) w oknie zdarzenia ±30 min.
Zwraca: confirmed / no_coverage / not_confirmed + precyzyjne czasy (sekundowe).
ZASADA: poza zakresem eventlogu → 'no_coverage' (NIE 'not_confirmed') — brak pokrycia ≠ brak zdarzenia.
Czasy eventlogu = LOKALNE (CEST/CET) → konwersja do UTC.
"""
import csv, sys, datetime as dt
from .pp_suppression import _local_offset

from . import paths as _cfg
EVLOG = _cfg.EVLOG_CSV
SYS2OLT = [("prusc", "prusce"), ("kiedr", "kiedrowo"), ("parkowo", "parkowo"), ("rogoz", "rogozno"),
           ("budki", "nowe_budki"), ("slawic", "slawa"), ("slawa", "slawa"), ("roszk", "roszkowo"),
           ("pleszew", "pleszew"), ("dobrz", "dobrzyca"), ("czerm", "czermin"),
           ("koscie", "koscielec"), ("chelm", "chelmce")]

def _olt_of(sysname):
    s = (sysname or "").lower()
    for k, v in SYS2OLT:
        if k in s: return v
    return None

def load_eventlog(path=EVLOG):
    ev = []
    for x in csv.DictReader(open(path, encoding="utf-8", errors="replace"), delimiter=";"):
        m = x.get("message") or ""
        is_state = ("changed to Down" in m) or ("changed to Up" in m)
        is_volt = (x.get("type") == "voltage") or ("voltage" in m.lower()) or ("napięci" in m.lower())
        if not (is_state or is_volt): continue
        try: t_loc = dt.datetime.fromisoformat(x["datetime"])
        except Exception: continue
        ev.append({"utc": t_loc - _local_offset(t_loc), "olt": _olt_of(x.get("sysName")),
                   "sys": x.get("sysName"), "down": "changed to Down" in m,
                   "kind": "voltage" if is_volt else "state", "msg": m[:100]})
    ev.sort(key=lambda e: e["utc"])
    cover = (min(e["utc"] for e in ev), max(e["utc"] for e in ev)) if ev else None
    return ev, cover

def power_warning(olts, t0_utc, ev=None, cover=None, back_h=3):
    """Polityka Barta dla power_or_node: czy PRZED zanikiem było ostrzeżenie siłowni (voltage)?
    warned = zasilanie (baterie ~1-2 h, potem weryfikacja formalna);
    no_warning = podejrzenie transport/OPL -> mail weryfikacyjny po 10 min."""
    if ev is None: ev, cover = load_eventlog()
    if cover is None or t0_utc > cover[1] or t0_utc < cover[0]:
        return {"status": "no_coverage", "note": "brak danych sensora w eksporcie — sprawdź maile siłowni ręcznie"}
    win0 = t0_utc - dt.timedelta(hours=back_h)
    hits = [e for e in ev if e["kind"] == "voltage" and e["olt"] in set(olts)
            and win0 <= e["utc"] <= t0_utc + dt.timedelta(minutes=10)]
    if hits:
        return {"status": "warned", "first_warning_utc": str(min(h["utc"] for h in hits)),
                "messages": [h["msg"] for h in hits[:3]]}
    return {"status": "no_warning"}

def confirm(event, ev=None, cover=None, margin_back_min=120, margin_fwd_min=30):
    """event = model dowodów z c_diagnose. Margines wstecz 2 h — detekcja RRA (konsolidacja
    slotu + debounce) jest zawsze PO realnym padnięciu, eventlog ICMP łapie je wcześniej."""
    if ev is None: ev, cover = load_eventlog()
    t0 = dt.datetime.fromisoformat(event["time_window"]["start_utc"])
    t1 = dt.datetime.fromisoformat(event["time_window"]["end_utc"])
    if cover is None or t0 > cover[1] or t1 < cover[0]:
        return {"status": "no_coverage", "note": f"eventlog nie pokrywa okna (zakres do {cover[1] if cover else '—'})"}
    olts = set(event["affected_scope"]["olts"])
    hits = [e for e in ev if e["olt"] in olts and e["kind"] == "state" and e["down"]
            and t0 - dt.timedelta(minutes=margin_back_min) <= e["utc"] <= t1 + dt.timedelta(minutes=margin_fwd_min)]
    ups = [e for e in ev if e["olt"] in olts and e["kind"] == "state" and not e["down"]
           and t0 <= e["utc"] <= t1 + dt.timedelta(hours=3)]
    if hits:
        return {"status": "confirmed", "n_devices": len(hits),
                "first_down_utc": str(min(h["utc"] for h in hits)),
                "recovery_utc": str(min(u["utc"] for u in ups)) if ups else None,
                "devices": sorted({h["sys"] for h in hits})}
    return {"status": "not_confirmed",
            "note": "brak Device-Down w oknie — dla sygnatury −80000 (pole światłowodowe) to SPÓJNE (węzeł żył)"}

def enrich(events):
    """Dokłada potwierdzenie do listy modeli dowodów (in place) + podbija confidence.
    Dla power_or_node stosuje POLITYKĘ BARTA (2026-07-04): gałąź wg ostrzeżenia siłowni."""
    ev, cover = load_eventlog()
    for e in events:
        c = confirm(e, ev, cover)
        e["signal"].setdefault("sources", [])
        e["confirmation_librenms"] = c
        if e["diagnosis"]["class"] == "power_or_node":
            t0 = dt.datetime.fromisoformat(e["time_window"]["start_utc"])
            pw = power_warning(e["affected_scope"]["olts"], t0, ev, cover)
            e["power_warning"] = pw
            dur_h = (dt.datetime.fromisoformat(e["time_window"]["end_utc"]) - t0).total_seconds() / 3600
            if pw["status"] == "warned":
                e["diagnosis"]["podtyp"] = "zasilanie_potwierdzone_silownia"
                dur_min = dur_h * 60
                e["diagnosis"]["recommended_action"] = (
                    f"ZASILANIE (siłownia ostrzegła {pw['first_warning_utc'][11:16]} UTC). "
                    f"Zanik trwa/trwał {dur_min:.0f} min" + (
                        " (>50 min = ponad baterie) → 1) WERYFIKACJA FORMALNA: opłacone rachunki za prąd; "
                        "2) sprawdź komunikaty Enea Operator o planowych wyłączeniach dla obszaru "
                        "(operator.enea.pl → wyłączenia); 3) wyjazd z agregatem."
                        if dur_min > 50 else
                        " (≤50 min — w zakresie baterii) → obserwuj, przygotuj agregat; "
                        "równolegle sprawdź komunikaty Enea o wyłączeniach dla obszaru."))
            elif pw["status"] == "no_warning":
                e["diagnosis"]["podtyp"] = "brak_ostrzezenia_silowni"
                e["diagnosis"]["recommended_action"] = (
                    "BRAK ostrzeżenia siłowni przed zanikiem → to raczej NIE prąd, podejrzenie łącza/transportu OPL. "
                    "Po 10 min od detekcji: mail weryfikacyjny do OPL wg wzoru "
                    "(07_outputs/wzor_mail_OPL.md) z danymi technicznymi łącza tej lokalizacji.")
            else:
                e["diagnosis"]["podtyp"] = "sensor_bez_pokrycia"
                e["diagnosis"]["recommended_action"] += (
                    " | UWAGA: eksport sensorów nie pokrywa okresu — sprawdź maile siłowni ręcznie "
                    "(gałąź: było ostrzeżenie=zasilanie/rachunki; brak=mail do OPL po 10 min).")
        if c["status"] == "confirmed":
            if "librenms" not in e["signal"]["sources"]: e["signal"]["sources"].append("librenms")
            e["signal"]["confidence"] = min(0.98, (e["signal"].get("confidence") or 0.8) + 0.1)
            e["diagnosis"]["confidence"] = min(0.98, (e["diagnosis"].get("confidence") or 0.5) + 0.1)
            if c.get("first_down_utc"):   # precyzyjny czas z eventlogu (sekundy) zamiast slotu RRA
                e["time_window"]["start_utc_precise"] = c["first_down_utc"]
                e["time_window"]["source"] = "librenms_eventlog+rrd"
    return events

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    import c_detect as CD, c_diagnose as DG
    RRD = r"F:/BRT/00.Informatyka_II_stopień/mgr/02_dane/raw/Cacti_RRD_2026-06-03/"
    inc, _ = CD.replay(RRD, rra_idx=5, debounce_slots=1, verbose=False)
    events = enrich(DG.diagnose(inc))
    print("=== POTWIERDZENIA LibreNMS (multi-source) ===")
    for e in events:
        c = e["confirmation_librenms"]; d = e["diagnosis"]
        extra = ""
        if c["status"] == "confirmed":
            extra = f" | down={c['first_down_utc'][11:19]} rec={str(c.get('recovery_utc'))[11:19]} dev={len(c['devices'])}"
        print(f"  {e['event_id']}: {d['class']:24} conf={d['confidence']:<5} -> {c['status']}{extra}")
        if c["status"] == "confirmed":
            print(f"     urządzenia: {', '.join(c['devices'][:6])}")
