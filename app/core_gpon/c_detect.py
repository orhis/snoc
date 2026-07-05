# -*- coding: utf-8 -*-
"""
c_detect — detektor batch (ścieżka A) z polityką operatorską Barta (2026-07-04):
  1. debounce 5/10 min: ONT dark w slocie t → potwierdź w t+5 i t+10 → nie wróciło = kandydat
  2. 1 ONT = BOK (nie alarmujemy); ≥2 ONT jednocześnie + blisko topologicznie = incydent
  3. coverage z saturacji per element (mała saturacja → 2/2 dark = mocny sygnał)
  4. sygnatura zgaśnięcia: −80000 (oltRx, pole światłowodowe) vs NaN (węzeł nieosiągalny)
  5. suppression prac planowych (pp_suppression)
Źródło: 5-min RRA MIN (idx 4, retencja ~50 h) — SLA 10 min osiągalne przy skanie co 5 min.
Replay: przebieg po historii pulla.
"""
import sys, csv, glob, math, datetime as dt
from collections import defaultdict
from .rrd_los import read_rra
from . import topo_localize as TL
from . import pp_suppression as PP

from . import paths as _cfg
KP = _cfg.KLUCZ_CSV

def load_series(rrd_dir, rra_idx=4):
    """ONT -> {t: oltRx} z 5-min RRA MIN; tylko ONT z żywym baseline."""
    kp = list(csv.DictReader(open(KP, encoding="utf-8", errors="replace"), delimiter=";"))
    ser, port_of, olt_of = {}, {}, {}
    for x in kp:
        cid = x["cacti_id_optical_new"].strip()
        if not cid: continue
        fns = glob.glob(rrd_dir + f"olt-{x['olt']}_oltrxopticallevel_{cid}.rrd")
        if not fns: continue
        try: lu, step, s = read_rra(fns[0], rra_idx=rra_idx, ds_name="oltRxOpticalLevel")
        except Exception: continue
        alive = [v for _, v in s if not math.isnan(v) and -60000 < v < -5000]
        if len(alive) <= 20: continue
        oid = f'{x["olt"]}|{x["port_gpon"]}|{x["ont_index"]}'
        ser[oid] = dict(s); port_of[oid] = x["port_gpon"]; olt_of[oid] = x["olt"]
    return ser, port_of, olt_of, step

LOS = lambda v: (not math.isnan(v)) and v <= -79000
NOD = lambda v: math.isnan(v)          # brak odpytu (węzeł?)

def replay(rrd_dir, topo=None, pp=None, min_cluster=2, debounce_slots=2,
           cov_threshold=0.5, rra_idx=4, verbose=True):
    """Przebieg po historii wg polityki Barta:
    klaster = ONT które ZGASŁY w tym samym oknie (nie: są ciemne) — „w tym samym momencie";
    alarm gdy n>=2 ORAZ blisko topologicznie (coverage>=próg pod wspólnym elementem);
    n==1 -> BOK-log; niski coverage -> „niezależne zgaśnięcia" -> BOK-log."""
    T = topo or TL.load()
    pp = pp if pp is not None else PP.load_pp()
    ser, port_of, olt_of, step = load_series(rrd_dir, rra_idx=rra_idx)
    slots = sorted({t for o in ser for t in ser[o]})
    if verbose:
        print(f"ONT={len(ser)} | slot={step}s | okno: "
              f"{dt.datetime.utcfromtimestamp(slots[0]):%m-%d %H:%M} .. {dt.datetime.utcfromtimestamp(slots[-1]):%m-%d %H:%M} UTC")
    flaky = {o for o in ser if sum(1 for v in ser[o].values() if LOS(v) or NOD(v)) >= 0.6*len(ser[o])}
    def dark_at(tt, o): return tt in ser[o] and (LOS(ser[o][tt]) or NOD(ser[o][tt]))
    incidents, bok_log, open_inc = [], [], {}
    for i, t in enumerate(slots):
        if i <= debounce_slots: continue
        # FRESH-dark z debounce: żywy w t-3, dark w t-2,t-1,t (zgasł ~10-15 min temu, nie wrócił)
        fresh = [o for o in ser if o not in flaky
                 and not dark_at(slots[i-debounce_slots-1], o)
                 and all(dark_at(slots[i-k], o) for k in range(debounce_slots+1))]
        # aktualizacja otwartych incydentów (eskalacja / domknięcie)
        for key in list(open_inc):
            inc = open_inc[key]
            still = [o for o in inc["onts"] if dark_at(t, o)]
            if still: inc["end_utc"] = t
            else: del open_inc[key]
        if not fresh: continue
        def try_cluster(onts):
            """Hierarchiczne klastrowanie: całość → jak cov niski, podział po słupkach.
            Zwraca (zaakceptowane_klastry [(onts, r)], odrzucone_onts)."""
            if len(onts) < min_cluster: return [], onts
            r = TL.localize(T, onts)
            cov = r.get("coverage_ratio") or 0.0
            if r.get("resolved") and cov >= cov_threshold: return [(onts, r)], []
            # podział po słupku (równoległe zdarzenia na tym samym OLT)
            by_sl = defaultdict(list)
            for o in onts: by_sl[T.ont_node.get(o)].append(o)
            acc, rej = [], []
            for sl, grp in by_sl.items():
                if sl is None or len(grp) < min_cluster: rej += grp; continue
                # >=2 fresh na TYM SAMYM słupku = blisko topologicznie z definicji -> incydent;
                # coverage zostaje jako sygnał diagnozy (cov~1: tranzyt przecięty / niski: splitter lokalny)
                r2 = TL.localize(T, grp)
                if r2.get("resolved"): acc.append((grp, r2))
                else: rej += grp
            return acc, rej
        by_olt = defaultdict(list)
        for o in fresh: by_olt[olt_of[o]].append(o)
        for olt, onts in by_olt.items():
            # dolej do otwartego incydentu, jeśli łączny coverage się broni (to samo zdarzenie rośnie)
            open_keys = [k for k in open_inc if k[0] == olt]
            if open_keys:
                k0 = open_keys[0]; inc = open_inc[k0]
                r_joint = TL.localize(T, sorted(set(inc["onts"]) | set(onts)))
                cj = r_joint.get("coverage_ratio") or 0.0
                if r_joint.get("resolved") and cj >= cov_threshold * 0.6:
                    inc["onts"] = sorted(set(inc["onts"]) | set(onts))
                    inc["n_max"] = max(inc["n_max"], len(inc["onts"]))
                    inc["localize"] = r_joint.get("common_element")
                    inc["coverage"], inc["confidence"] = cj, r_joint.get("confidence")
                    continue
                # nie skleja się -> potraktuj jako osobnego kandydata (równoległy incydent)
            acc, rej = try_cluster(onts)
            if rej: bok_log.append((t, olt, rej))               # 1 ONT / rozrzucone -> BOK
            for grp, r in acc:
                sig = "wezel_nieosiagalny(NaN)" if all(NOD(ser[o][t]) for o in grp) else "LOS_optyczny(-80000)"
                supp = PP.check(dt.datetime.utcfromtimestamp(t), pp=pp)
                el = (r.get("common_element") or {}).get("label", "?")
                inc = {"start_utc": t, "end_utc": t, "olt": olt, "n_onts": len(grp), "n_max": len(grp),
                       "n_slupki": len({T.ont_node.get(o) for o in grp if T.ont_node.get(o)}),
                       "sygnatura": sig, "suppressed_PP": supp["suppressed"],
                       "localize": r.get("common_element"), "coverage": r.get("coverage_ratio"),
                       "confidence": r.get("confidence"), "onts": sorted(grp)}
                open_inc[(olt, el)] = inc; incidents.append(inc)
    return incidents, bok_log

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    RRD = r"F:/BRT/00.Informatyka_II_stopień/mgr/02_dane/raw/Cacti_RRD_2026-06-03/"
    print("=== REPLAY 5-min RRA (~50 h pulla 06-03) — polityka Barta: fresh-klaster >=2 + coverage>=0.5 + debounce 10 min ===")
    inc, bok = replay(RRD)
    print(f"\nINCYDENTY (alarm): {len(inc)} | wpisy BOK-log (1 ONT / rozrzucone): {len(bok)}")
    for x in inc:
        s = dt.datetime.utcfromtimestamp(x["start_utc"]); e = dt.datetime.utcfromtimestamp(x["end_utc"])
        dur = max(0, (x["end_utc"]-x["start_utc"])/60)
        print(f"\n  🔔 [{x['olt']}] {s:%m-%d %H:%M}–{e:%m-%d %H:%M} UTC ({dur:.0f} min) | ONT start={x['n_onts']} max={x['n_max']} | {x['sygnatura']}")
        print(f"     localize: {x['localize']} | coverage={x['coverage']} conf={x['confidence']} | PP_suppressed={x['suppressed_PP']}")
    from collections import Counter
    print("\nBOK-log wg OLT:", dict(Counter(olt for _, olt, _ in bok).most_common()))
