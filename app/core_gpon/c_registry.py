# -*- coding: utf-8 -*-
"""
c_registry — trwały rejestr incydentów (fundament 2: pamięć systemu).
- append z deduplikacją po event_id (re-run replay nie dubluje),
- CSV (przegląd/Excel) + JSONL (pełne modele dowodów),
- kolumny feedbacku operatora (verdict/notatka) — NIE nadpisywane przy update,
- recydywa: ile wcześniejszych incydentów na tym samym elemencie/OLT.
"""
import csv, json, os, sys
from . import paths as _cfg
OUT = _cfg.DATA_DIR.rstrip("/\\") + "/"
CSV_P, JSONL_P = OUT + "incident_registry.csv", OUT + "incident_registry.jsonl"
COLS = ["event_id", "start_utc", "end_utc", "class", "confidence", "olts", "n_onts",
        "common_element", "coverage", "signal", "recommended_action",
        "recydywa_element", "operator_verdict", "operator_note"]

def _load():
    if not os.path.exists(CSV_P): return {}
    return {r["event_id"]: r for r in csv.DictReader(open(CSV_P, encoding="utf-8"), delimiter=";")}

def register(events):
    """events = lista modeli dowodów z c_diagnose.diagnose(). Zwraca (nowe, zaktualizowane)."""
    os.makedirs(OUT, exist_ok=True)
    reg = _load()
    # recydywa: policz wystąpienia elementu w dotychczasowym rejestrze
    hist = {}
    for r in reg.values():
        el = r.get("common_element") or ""
        if el: hist[el] = hist.get(el, 0) + 1
    nowe = upd = 0
    import datetime as dt
    def _ts(x):
        try: return dt.datetime.fromisoformat(x).timestamp()
        except Exception: return 0
    for ev in events:
        eid = ev["event_id"]; d = ev["diagnosis"]; ti = ev["topology_inference"]; s = ev["affected_scope"]
        # scal z istniejącym: ten sam OLT-set + klasa + start w ±1 h (to samo zdarzenie z innego RRA)
        if eid not in reg:
            t0 = _ts(ev["time_window"]["start_utc"])
            for r in reg.values():
                if (r["olts"] == ",".join(s["olts"])
                        and abs(_ts(r["start_utc"]) - t0) <= 3600):
                    eid = r["event_id"]; break
        el = ti.get("common_element") or ""
        row = {"event_id": eid, "start_utc": ev["time_window"]["start_utc"], "end_utc": ev["time_window"]["end_utc"],
               "class": d["class"], "confidence": d["confidence"], "olts": ",".join(s["olts"]),
               "n_onts": s["onts"], "common_element": el, "coverage": ti.get("coverage_ratio"),
               "signal": ev["signal"]["value"], "recommended_action": d["recommended_action"],
               "recydywa_element": hist.get(el, 0),
               "operator_verdict": "", "operator_note": ""}
        if eid in reg:   # zachowaj feedback operatora
            row["operator_verdict"] = reg[eid].get("operator_verdict", "")
            row["operator_note"] = reg[eid].get("operator_note", "")
            row["recydywa_element"] = reg[eid].get("recydywa_element", row["recydywa_element"])
            upd += 1
        else:
            nowe += 1
        reg[eid] = row
    # recydywa przeliczana globalnie: liczba WCZEŚNIEJSZYCH zdarzeń na tym samym elemencie
    ordered = sorted(reg.values(), key=lambda x: x["start_utc"])
    seen_el = {}
    for r in ordered:
        el = r.get("common_element") or ""
        r["recydywa_element"] = seen_el.get(el, 0) if el else 0
        if el: seen_el[el] = seen_el.get(el, 0) + 1
    with open(CSV_P, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, delimiter=";"); w.writeheader()
        for r in ordered: w.writerow(r)
    with open(JSONL_P, "a", encoding="utf-8") as f:
        for ev in events: f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    return nowe, upd

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    import c_detect as CD, c_diagnose as DG
    RRD = r"F:/BRT/00.Informatyka_II_stopień/mgr/02_dane/raw/Cacti_RRD_2026-06-03/"
    inc30, _ = CD.replay(RRD, rra_idx=5, debounce_slots=1, verbose=False)
    inc5, _ = CD.replay(RRD, rra_idx=4, verbose=False)
    ev = DG.diagnose(inc30) + DG.diagnose(inc5)
    n, u = register(ev)
    print(f"rejestr: +{n} nowych, {u} zaktualizowanych -> {CSV_P}")
    for r in csv.DictReader(open(CSV_P, encoding="utf-8"), delimiter=";"):
        print(f"  {r['event_id']}: {r['class']} ({r['confidence']}) | {r['olts']} | ONT={r['n_onts']} | el={r['common_element']} | recydywa={r['recydywa_element']}")
    # test idempotencji
    n2, u2 = register(ev)
    print(f"re-run (idempotencja): +{n2} nowych, {u2} zaktualizowanych (oczekiwane: +0)")
