# -*- coding: utf-8 -*-
"""
pp_suppression — tłumienie fałszywych alarmów w oknach prac planowych OPL/EPIX.
Źródło: mgr/02_dane/processed/pp_opl_v2.csv (70 PP, parsowane z .msg SPPTP).
Czasy PP = lokalne (Europe/Warsaw); zdarzenia RRD = UTC → konwersja tutaj.
check(event_utc) -> {suppressed, matches[], note} z buforem ±30 min.
"""
import csv, datetime as dt
from . import paths as _cfg
PP_CSV = _cfg.PP_CSV
BUF = dt.timedelta(minutes=30)

def _local_offset(d):
    """Przybliżenie Europe/Warsaw bez tzdata: CEST (UTC+2) ostatnia niedziela III–X, inaczej CET (UTC+1)."""
    def last_sun(y, m):
        x = dt.date(y, m + 1, 1) - dt.timedelta(days=1) if m < 12 else dt.date(y, 12, 31)
        return x - dt.timedelta(days=(x.weekday() + 1) % 7)
    start = dt.datetime.combine(last_sun(d.year, 3), dt.time(2))
    end = dt.datetime.combine(last_sun(d.year, 10), dt.time(3))
    return dt.timedelta(hours=2) if start <= d < end else dt.timedelta(hours=1)

def load_pp(path=PP_CSV):
    out = []
    for r in csv.DictReader(open(path, encoding="utf-8", errors="replace"), delimiter=";"):
        try:
            s = dt.datetime.fromisoformat(r["time_start"])
            e = dt.datetime.fromisoformat(r["time_end"])
        except Exception:
            continue
        # lokalne -> UTC
        s_utc, e_utc = s - _local_offset(s), e - _local_offset(e)
        out.append({"pp_id": r["pp_id"], "start_utc": s_utc, "end_utc": e_utc,
                    "odbiorca": r.get("odbiorca", ""), "locations": (r.get("locations") or "").strip(),
                    "subject": r.get("subject", "")})
    return out

def check(event_start_utc, event_end_utc=None, pp=None):
    """Czy zdarzenie (UTC, naive) wpada w okno PP ±30 min. Zwraca dict z dopasowaniami."""
    pp = pp if pp is not None else load_pp()
    e0 = event_start_utc
    e1 = event_end_utc or event_start_utc
    hits = [p for p in pp if p["start_utc"] - BUF <= e1 and e0 <= p["end_utc"] + BUF]
    return {"suppressed": bool(hits),
            "matches": [{"pp_id": p["pp_id"], "start_utc": str(p["start_utc"]),
                         "end_utc": str(p["end_utc"]), "locations": p["locations"]} for p in hits],
            "note": ("okno pracy planowej OPL/EPIX — wstrzymaj eskalację, oznacz jako planned"
                     if hits else "brak PP w oknie — zdarzenie NIE jest pracą planową")}

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    pp = load_pp()
    print(f"PP załadowane: {len(pp)} | zakres: {min(p['start_utc'] for p in pp):%Y-%m-%d} .. {max(p['end_utc'] for p in pp):%Y-%m-%d}")
    loc = sum(1 for p in pp if p["locations"])
    print(f"PP z lokalizacjami: {loc}/{len(pp)} (reszta = suppression tylko czasowe)")
    # TESTY na znanych zdarzeniach
    tests = [
        ("gold 4-OLT Orange (awaria!)", dt.datetime(2026, 5, 26, 8, 30), dt.datetime(2026, 5, 26, 19, 35), False),
        ("B06 nowe_budki (power!)", dt.datetime(2026, 6, 2, 9, 30), dt.datetime(2026, 6, 2, 14, 46), False),
        ("E03 testy kontrolowane", dt.datetime(2026, 5, 29, 10, 0), dt.datetime(2026, 5, 29, 11, 0), False),
    ]
    print("\n== testy suppression (oczekiwane: awarie NIE-suppressed) ==")
    ok = True
    for name, s, e, expect in tests:
        r = check(s, e, pp)
        verdict = "✅" if r["suppressed"] == expect else "❌ BŁĄD"
        if r["suppressed"] != expect: ok = False
        print(f"  {verdict} {name}: suppressed={r['suppressed']} {('-> '+str(r['matches'])) if r['matches'] else ''}")
    # sanity: znajdź PP która by COŚ tłumiła (najbliższa datom RRD)
    inwin = [p for p in pp if dt.datetime(2026, 5, 1) <= p["start_utc"] <= dt.datetime(2026, 6, 10)]
    print(f"\nPP w oknie danych RRD (05-06.2026): {len(inwin)}")
    for p in inwin: print(f"   PP {p['pp_id']}: {p['start_utc']:%m-%d %H:%M}–{p['end_utc']:%H:%M} UTC | {p['subject'][:44]}")
    print("\nWYNIK:", "wszystkie testy OK" if ok else "SĄ BŁĘDY")
