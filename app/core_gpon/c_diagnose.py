# -*- coding: utf-8 -*-
"""
c_diagnose — warstwa diagnozy: incydenty z c_detect → MODEL DOWODÓW (KONCEPCJA_C §4).
Drzewo (deterministyczne, §5 + poziom 0):
  0) suppressed_PP                                → planned_maintenance
  1) ≥2 OLT w tym samym oknie (korelacja czasowa) → outage_upstream_or_opl (klasa 10)
  2) NaN (węzeł nieosiągalny) + większość OLT     → power_or_node / olt_unreachable
  3) −80000 (pole światłowodowe):
     a) port dark/total ≥ 0.9                     → gpon_port (wkładka/patchcord na OLT)
     b) częściowy + coverage ≥ 0.5 pod elementem  → splitter_or_branch (element z localize)
     c) inaczej                                   → uncertain (abstain)
Topology-honest: cannot_resolve_below gdy element = PE/słupek (splitter poniżej rozdzielczości).
"""
import sys, csv, json, datetime as dt
from collections import defaultdict

from . import paths as _cfg
KP = _cfg.KLUCZ_CSV
CROSS_OLT_WINDOW_S = 3600   # incydenty startujące w tym oknie na >=2 OLT = jedno zdarzenie upstream

# Mapowanie klas C -> taksonomia pracy mgr (klasy 1-11; stan po walidacji R2/R3):
KLASA_TAKSONOMIA = {
    "outage_upstream_or_opl": "10 (awaria OPL/Orange; jeśli ASR/EPIX-side -> 6b)",
    "power_or_node":          "6a (nasza szafa: zasilanie/OLT wezla)",
    "gpon_port":              "6a (nasz sprzet OLT: wkladka/port)",
    "splitter_or_branch":     "5 (kabel/splitter grupowy) lub 7 gdy 1 klient",
    "power_area_customers":   "— (nowa; poza siecia: energetyka u klientow, nie-awaria)",
    "planned_maintenance":    "4 (prace planowe Orange/EPIX)",
    "uncertain":              "do_review",
}

REKOMENDACJA = {
    "planned_maintenance":    "okno pracy planowej OPL/EPIX — wstrzymaj eskalację, obserwuj do końca okna",
    "outage_upstream_or_opl": "zdarzenie ponad naszą topologią (≥2 węzły synchronicznie) — sprawdź ASR/transport, przygotuj zgłoszenie do OPL (spptp/cs)",
    "power_or_node":          "węzeł nieosiągalny — sprawdź zasilanie/agregat/OLT w lokalizacji; eventlog voltage jako potwierdzenie",
    "gpon_port":              "pełny pad portu GPON — sprawdź wkładkę/patchcord na OLT (strona centralowa), nie wysyłaj technika w pole",
    "splitter_or_branch":     "częściowy pad za wspólnym elementem — technik na wskazany element (odcinek/mufa/splitter za nim)",
    "power_area_customers":   "wzorzec wyłączenia prądu w obszarze (plama sąsiednich słupków, OLT/siłownia OK) — sprawdź komunikaty Enea Operator o planowych wyłączeniach (operator.enea.pl → wyłączenia); NIE wysyłaj technika, czekaj na samoistny powrót",
    "uncertain":              "sygnał niejednoznaczny — obserwuj; eskaluj dopiero przy 2. źródle (zgłoszenie BOK / eventlog)",
}

def _port_totals():
    tot = defaultdict(int)
    for x in csv.DictReader(open(KP, encoding="utf-8", errors="replace"), delimiter=";"):
        if x["cacti_id_optical_new"].strip():
            tot[(x["olt"], x["port_gpon"])] += 1
    return tot

def _olt_totals():
    tot = defaultdict(int)
    for x in csv.DictReader(open(KP, encoding="utf-8", errors="replace"), delimiter=";"):
        if x["cacti_id_optical_new"].strip():
            tot[x["olt"]] += 1
    return tot

def diagnose(incidents):
    """Lista incydentów (c_detect.replay) → lista modeli dowodów (jeden per zdarzenie;
    incydenty cross-OLT sklejane w JEDNO zdarzenie upstream)."""
    port_tot, olt_tot = _port_totals(), _olt_totals()
    # 1) grupowanie po czasie startu: >=2 OLT -> upstream; 1 OLT wiele podklastrów -> „plama" (scal)
    groups, used = [], set()
    for i, a in enumerate(incidents):
        if i in used: continue
        grp = [a]; used.add(i)
        for j, b in enumerate(incidents):
            if j in used: continue
            if abs(a["start_utc"] - b["start_utc"]) <= CROSS_OLT_WINDOW_S:
                grp.append(b); used.add(j)
        groups.append(grp)
    out = []
    for grp in groups:
        inc = max(grp, key=lambda x: x["n_max"])
        t0 = min(x["start_utc"] for x in grp); t1 = max(x["end_utc"] for x in grp)
        olts = sorted({x["olt"] for x in grp})
        n_onts = sum(x["n_max"] for x in grp)
        n_slupki = sum(x.get("n_slupki", 1) for x in grp)
        if len(grp) > 1 and len(olts) == 1:
            # plama podklastrów na jednym OLT: coverage = średnia ważona, element = najpłytszy wspólny opis
            inc = dict(inc); inc["n_slupki"] = n_slupki
            inc["onts"] = sorted({o for x in grp for o in x["onts"]})
            covs = [x.get("coverage") for x in grp if x.get("coverage") is not None]
            inc["coverage"] = round(sum(covs) / len(covs), 3) if covs else None
        sig = inc["sygnatura"]
        # ---- drzewo ----
        cannot_below, missing = False, []
        if any(x["suppressed_PP"] for x in grp):
            klasa, conf = "planned_maintenance", 0.9
        elif len(olts) >= 2:
            klasa = "outage_upstream_or_opl"
            conf = min(0.95, 0.6 + 0.1 * len(olts))     # synchro wielu węzłów = mocny sygnał
            cannot_below = True; missing = ["topologia_powyzej_OLT(Orange)"]
        elif "NaN" in sig and n_onts >= 0.6 * max(1, olt_tot.get(inc["olt"], 0)):
            klasa, conf = "power_or_node", 0.85
            missing = ["eventlog_voltage(do_potwierdzenia)"]
        else:
            # Reguła C per-port (ratio >= 0.9 -> gpon_port)
            per_port = defaultdict(int)
            for o in inc["onts"]:
                olt, port, _ = o.split("|"); per_port[(olt, port)] += 1
            full_ports = [p for p, n in per_port.items() if port_tot.get(p, 0) and n / port_tot[p] >= 0.9]
            cov = inc.get("coverage") or 0.0
            n_slupki = len({o.rsplit("|", 1)[0] for o in inc["onts"]})  # przybliżenie; realnie: słupki
            if full_ports and len(full_ports) == len(per_port):
                klasa, conf = "gpon_port", 0.8
                missing = ["potwierdzenie_na_OLT(wkladka)"]
            elif inc.get("n_slupki", n_slupki) >= 3 and 0.2 <= cov < 0.9:
                # „plama" wielu sąsiednich słupków z umiarkowanym coverage = prąd w obszarze
                # (potwierdzone 30.05 kiedrowo: 5 słupków, cov 0.35, OLT/siłownia OK, powrót ~1h, 0 zgłoszeń)
                klasa, conf = "power_area_customers", 0.6
                missing = ["wylaczenia_energetyki(do_potwierdzenia)", "dying_gasp(logi_OLT)"]
            elif cov >= 0.5 and inc.get("localize"):
                klasa = "splitter_or_branch"
                conf = round(0.5 + 0.45 * min(cov, 1.0), 2)
                el = inc["localize"]
                if isinstance(el, dict) and str(el.get("label", "")).startswith(("PE/", "J/", "ZK/")):
                    cannot_below = True; missing = ["splitter_ponizej_rozdzielczosci_grafu"]
            else:
                klasa, conf = "uncertain", 0.3
        ev = {
            "event_id": f"INC-{dt.datetime.utcfromtimestamp(t0):%Y%m%d-%H%M}-{olts[0]}",
            "time_window": {"start_utc": str(dt.datetime.utcfromtimestamp(t0)),
                            "end_utc": str(dt.datetime.utcfromtimestamp(t1)),
                            "source": "rrd_min_rra", "confidence": 0.9},
            "signal": {"value": sig, "sources": ["rrd"], "n_onts": n_onts, "confidence": 0.85},
            "affected_scope": {"olts": olts, "onts": n_onts,
                               "hp": (inc.get("localize") or {}).get("hp") if isinstance(inc.get("localize"), dict) else None,
                               "sources": ["rrd", "topology"], "confidence": 0.8},
            "topology_inference": {
                "lowest_reliable_common_level": ("multi-OLT/upstream" if len(olts) >= 2
                                                 else (inc["localize"].get("type") if isinstance(inc.get("localize"), dict) else None)),
                "common_element": (inc["localize"].get("label") if isinstance(inc.get("localize"), dict) else None),
                "coverage_ratio": inc.get("coverage"), "provenance": "graf_topo_repaired(authoritative+bridges)",
                "cannot_resolve_below": cannot_below, "missing_data": missing,
                "confidence": inc.get("confidence")},
            "diagnosis": {"class": klasa, "confidence": conf, "abstain": klasa == "uncertain",
                          "taksonomia_mgr": KLASA_TAKSONOMIA.get(klasa, "?"),
                          "recommended_action": REKOMENDACJA[klasa]},
        }
        out.append(ev)
    return out

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    import c_detect as CD
    RRD = r"F:/BRT/00.Informatyka_II_stopień/mgr/02_dane/raw/Cacti_RRD_2026-06-03/"
    print("=== TEST 1: replay 5-min (50 h) -> diagnoza B06 ===")
    inc5, _ = CD.replay(RRD, rra_idx=4, verbose=False)
    for ev in diagnose(inc5):
        print(json.dumps(ev, ensure_ascii=False, indent=1))
    print("\n=== TEST 2: replay 30-min (14 dni) -> diagnoza (oczekiwane: cross-OLT 26.05 = upstream) ===")
    inc30, _ = CD.replay(RRD, rra_idx=5, debounce_slots=1, verbose=False)
    for ev in diagnose(inc30):
        d = ev["diagnosis"]; s = ev["affected_scope"]
        print(f"  {ev['event_id']}: {d['class']} (conf {d['confidence']}) | OLT={s['olts']} ONT={s['onts']} | {ev['topology_inference']['common_element']}")
