# -*- coding: utf-8 -*-
"""
pipeline — jeden przebieg rdzenia: skan RRD → diagnoza → evidence freeze → confirmer → rejestr → raport.
(Transplantacja run_c.py z realtime/, przystosowana do pakietu app.core_gpon.)

Użycie (dev, z korzenia repo):
    .venv\\Scripts\\python -m app.core_gpon.pipeline [katalog_RRD]
Produkcja: wołane przez scheduler (T3) co 5 min; źródło = SNOC_RRD_DIR (żywy rra/ Cacti).
"""
import sys, os, glob, csv, datetime as dt
from . import paths as _cfg
from . import c_detect as CD, c_diagnose as DG, c_registry as REG

OUT = _cfg.DATA_DIR.rstrip("/\\") + "/"
RAW = _cfg.RRD_PULLS.rstrip("/\\") + "/"

def newest_pull():
    pulls = sorted(glob.glob(RAW + "Cacti_RRD_*"))
    return (pulls[-1] + "/") if pulls else None

def main(rrd_dir=None, rra=None, registry=None):
    """registry: modul z register(events) — default CSV (stdlib); app podaje registry_service (DB)."""
    REG_ = registry or REG
    os.makedirs(OUT, exist_ok=True)
    rrd_dir = rrd_dir or (_cfg.RRD_DIR or None) or newest_pull()
    print(f"[pipeline] źródło RRD: {rrd_dir}")
    before = set()
    if os.path.exists(REG.CSV_P):
        before = {r["event_id"] for r in csv.DictReader(open(REG.CSV_P, encoding="utf-8"), delimiter=";")}
    events, all_inc = [], []
    rras = [int(rra)] if rra else [4, 5]
    for idx in rras:
        db = _cfg.DEBOUNCE_SLOTS if idx == 4 else 1
        try:
            inc, bok = CD.replay(rrd_dir, rra_idx=idx, debounce_slots=db,
                                 min_cluster=_cfg.MIN_CLUSTER, cov_threshold=_cfg.COV_THRESHOLD,
                                 verbose=False)
        except Exception as e:
            print(f"[pipeline] RRA{idx}: pominięte ({e})"); continue
        all_inc += inc
        events += DG.diagnose(inc)
        print(f"[pipeline] RRA{idx}: kandydatów={len(inc)}, BOK={len(bok)}")
    try:
        from . import c_evidence as EV
        f, s, emp = EV.freeze(all_inc, rrd_dir)
        print(f"[pipeline] evidence freeze: +{f}, {s} już było, {emp} poza retencją")
    except Exception as e:
        print(f"[pipeline] freeze pominięty ({e})")
    try:
        from . import c_confirm as CF
        events = CF.enrich(events)
        nc = sum(1 for e in events if e.get("confirmation_librenms", {}).get("status") == "confirmed")
        print(f"[pipeline] confirmer: {nc}/{len(events)} potwierdzonych")
    except Exception as e:
        print(f"[pipeline] confirmer pominięty ({e})")
    n_new, n_upd = REG_.register(events)
    if registry is None and os.path.exists(REG.CSV_P):
        reg = list(csv.DictReader(open(REG.CSV_P, encoding="utf-8"), delimiter=";"))
        nowe = [r for r in reg if r["event_id"] not in before]
    else:   # rejestr w DB (T2): raportuj z tego przebiegu
        nowe = [{"event_id": e["event_id"], "start_utc": e["time_window"]["start_utc"],
                 "class": e["diagnosis"]["class"], "confidence": e["diagnosis"]["confidence"],
                 "olts": ",".join(e["affected_scope"]["olts"]), "n_onts": e["affected_scope"]["onts"],
                 "common_element": e["topology_inference"].get("common_element") or "",
                 "recommended_action": e["diagnosis"]["recommended_action"]}
                for e in events]
        reg = nowe
    rp = OUT + f"raport_{dt.date.today().isoformat()}.md"
    with open(rp, "w", encoding="utf-8") as f:
        f.write(f"# Raport SNOC — {dt.date.today().isoformat()}\n\nŹródło: `{rrd_dir}` | rejestr: {len(reg)} (+{n_new})\n\n")
        if nowe:
            f.write("| start (UTC) | klasa | conf | OLT | ONT | element | rekomendacja |\n|---|---|---|---|---|---|---|\n")
            for r in sorted(nowe, key=lambda x: x["start_utc"]):
                f.write(f"| {r['start_utc'][:16]} | **{r['class']}** | {r['confidence']} | {r['olts']} "
                        f"| {r['n_onts']} | {r['common_element']} | {r['recommended_action'][:90]} |\n")
        else:
            f.write("Brak nowych zdarzeń.\n")
    print(f"[pipeline] rejestr: +{n_new}/{n_upd} | raport: {rp}")
    return rp

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = sys.argv[1:]
    main(a[0] if a else None)
