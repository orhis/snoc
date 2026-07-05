# -*- coding: utf-8 -*-
"""
c_evidence — ZRZUT DOWODÓW przy zdarzeniu (evidence freeze).
Problem: 5-min RRA żyje ~50 h, 30-min ~14 dni — a spór z OPL/analiza może przyjść po tygodniach.
Rozwiązanie: przy każdym incydencie zapisujemy surowe przebiegi RRD dotkniętych ONT
(okno: start−2 h … end+2 h) do 07_outputs/zdarzenia/<event_id>/:
    przebiegi_rra{4,5}.csv  (ont;slot_utc;oltRx_raw)  +  meta.json (pełny incydent)
ZASADA: folder raz zapisany NIE jest nadpisywany (freeze = dowód; re-run po czasie
miałby już obcięte dane i by je zepsuł).
"""
import csv, json, os, sys, glob, math, datetime as dt
from .rrd_los import read_rra

from . import paths as _cfg
OUT = _cfg.zdarzenia_dir().rstrip("/\\") + "/"
KP = _cfg.KLUCZ_CSV
MARGIN_S = 2 * 3600

def _cid_map():
    m = {}
    for x in csv.DictReader(open(KP, encoding="utf-8", errors="replace"), delimiter=";"):
        if x["cacti_id_optical_new"].strip():
            m[f'{x["olt"]}|{x["port_gpon"]}|{x["ont_index"]}'] = (x["olt"], x["cacti_id_optical_new"].strip())
    return m

def freeze(incidents, rrd_dir, rras=(4, 5)):
    """incidents = lista z c_detect.replay (onts/olt/start_utc/end_utc).
    Zwraca (zamrożone, pominięte_istniejące, bez_danych)."""
    os.makedirs(OUT, exist_ok=True)
    cid = _cid_map()
    frozen = skipped = empty = 0
    for inc in incidents:
        eid = f"INC-{dt.datetime.utcfromtimestamp(inc['start_utc']):%Y%m%d-%H%M}-{inc['olt']}"
        d = OUT + eid + "/"
        if os.path.exists(d + "meta.json"):
            skipped += 1; continue                      # FREEZE: nigdy nie nadpisuj
        t0, t1 = inc["start_utc"] - MARGIN_S, inc["end_utc"] + MARGIN_S
        wrote_any = False
        os.makedirs(d, exist_ok=True)
        for rra in rras:
            rows = []
            for o in inc["onts"]:
                if o not in cid: continue
                olt, c = cid[o]
                fns = glob.glob(rrd_dir + f"olt-{olt}_oltrxopticallevel_{c}.rrd")
                if not fns: continue
                try: _, step, s = read_rra(fns[0], rra_idx=rra, ds_name="oltRxOpticalLevel")
                except Exception: continue
                for t, v in s:
                    if t0 <= t <= t1:
                        rows.append((o, dt.datetime.utcfromtimestamp(t).isoformat(),
                                     "" if math.isnan(v) else round(v, 1)))
            if rows:
                wrote_any = True
                with open(d + f"przebiegi_rra{rra}.csv", "w", encoding="utf-8", newline="") as f:
                    w = csv.writer(f, delimiter=";"); w.writerow(["ont", "slot_utc", "oltRx_raw"])
                    w.writerows(sorted(rows))
        meta = dict(inc); meta["frozen_at"] = dt.datetime.now().isoformat()
        meta["rrd_source"] = rrd_dir
        json.dump(meta, open(d + "meta.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
        if wrote_any: frozen += 1
        else: empty += 1                                 # meta jest, przebiegi poza retencją
    return frozen, skipped, empty

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    import c_detect as CD
    RRD = r"F:/BRT/00.Informatyka_II_stopień/mgr/02_dane/raw/Cacti_RRD_2026-06-03/"
    inc5, _ = CD.replay(RRD, rra_idx=4, verbose=False)
    inc30, _ = CD.replay(RRD, rra_idx=5, debounce_slots=1, verbose=False)
    f, s, e = freeze(inc5 + inc30, RRD)
    print(f"freeze: zamrożone={f} | pominięte(już były)={s} | meta-bez-przebiegów(poza retencją)={e}")
    for d in sorted(os.listdir(OUT)):
        files = os.listdir(OUT + d)
        sizes = {fn: os.path.getsize(OUT + d + "/" + fn) // 1024 for fn in files}
        print(f"  {d}: {sizes}")
