# -*- coding: utf-8 -*-
"""
Testy rdzenia domenowego (T1). Warstwy:
1) wiring — importy pakietu (zawsze),
2) topologia/localize — self-testy na artefaktach data/topo (skip gdy brak),
3) suppression PP + confirmer — zachowania kontraktowe na artefaktach (skip gdy brak).
Regresja goldów na RRD wymaga pulla (~1.2 GB, poza repo) — patrz test_pipeline_smoke (skip bez pulla).
"""
import os, datetime as dt
import pytest

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
HAS_TOPO = os.path.exists(os.path.join(DATA, "topo", "nodes.csv"))
HAS_PP = os.path.exists(os.path.join(DATA, "pp", "pp_opl_v2.csv"))
HAS_EVLOG = os.path.exists(os.path.join(DATA, "eventlog", "_all_eventlog.csv"))


def test_wiring_importy():
    from app.core_gpon import (rrd_los, topo_localize, pp_suppression,  # noqa: F401
                               c_detect, c_diagnose, c_confirm, c_evidence, c_registry, pipeline)


@pytest.mark.skipif(not HAS_TOPO, reason="brak data/topo (artefakt poza repo)")
class TestLocalize:
    @pytest.fixture(scope="class")
    def T(self):
        from app.core_gpon import topo_localize as TL
        return TL.load()

    def test_graf_zaladowany(self, T):
        assert len(T.adj) > 20000 and len(T.ont_node) > 700

    def test_pinpoint_slupka(self, T):
        """Padły wszystkie ONT jednego słupka -> localize wskazuje TEN słupek, coverage 1.0."""
        from app.core_gpon import topo_localize as TL
        nd, onts = sorted(T.ont_by_slupek.items(), key=lambda kv: -len(kv[1]))[3]
        r = TL.localize(T, onts)
        assert r["resolved"] and r["common_element"]["label"] == T.label[nd]
        assert r["coverage_ratio"] == 1.0

    def test_odmowa_multi_olt(self, T):
        """ONT z różnych OLT -> topology-honest: odmowa, nie zgadywanie."""
        from app.core_gpon import topo_localize as TL
        cand = sorted(T.ont_by_slupek.items(), key=lambda kv: -len(kv[1]))
        nd1, o1 = cand[3]
        nd2, o2 = next((m, o) for m, o in cand if T.root_of.get(m) != T.root_of.get(nd1))
        r = TL.localize(T, o1[:2] + o2[:2])
        assert not r["resolved"]


@pytest.mark.skipif(not HAS_PP, reason="brak data/pp")
class TestSuppressionPP:
    def test_goldy_nie_tlumione(self):
        """Realne awarie (26.05, 02.06) NIE mogą wpadać w okna prac planowych."""
        from app.core_gpon import pp_suppression as PP
        pp = PP.load_pp()
        assert len(pp) >= 60
        for t0 in (dt.datetime(2026, 5, 26, 8, 30), dt.datetime(2026, 6, 2, 9, 30)):
            assert not PP.check(t0, pp=pp)["suppressed"]

    def test_okno_pp_tlumi(self):
        """Zdarzenie w środku znanego okna PP (23.05 ~00:30 UTC) -> suppressed."""
        from app.core_gpon import pp_suppression as PP
        r = PP.check(dt.datetime(2026, 5, 23, 0, 30))
        assert r["suppressed"]


@pytest.mark.skipif(not HAS_EVLOG, reason="brak data/eventlog")
class TestConfirmer:
    def test_no_coverage_poza_zakresem(self):
        """Poza zakresem eventlogu = no_coverage, NIGDY 'not_confirmed' (zasada D6)."""
        from app.core_gpon import c_confirm as CF
        ev, cover = CF.load_eventlog()
        fake = {"time_window": {"start_utc": "2026-07-01 10:00:00", "end_utc": "2026-07-01 11:00:00"},
                "affected_scope": {"olts": ["nowe_budki"]}}
        assert CF.confirm(fake, ev, cover)["status"] == "no_coverage"

    def test_gold_26_05_confirmed(self):
        """Gold 4-OLT 26.05: potwierdzenie z sekundowym czasem down."""
        from app.core_gpon import c_confirm as CF
        ev, cover = CF.load_eventlog()
        gold = {"time_window": {"start_utc": "2026-05-26 09:00:00", "end_utc": "2026-05-26 19:35:00"},
                "affected_scope": {"olts": ["kiedrowo", "parkowo", "prusce", "rogozno"]}}
        r = CF.confirm(gold, ev, cover)
        assert r["status"] == "confirmed" and r["first_down_utc"].startswith("2026-05-26 07:5")


RRD_PULL = r"F:/BRT/00.Informatyka_II_stopień/mgr/02_dane/raw/Cacti_RRD_2026-06-03/"

@pytest.mark.skipif(not (HAS_TOPO and os.path.exists(RRD_PULL)), reason="brak pulla RRD (dev-only)")
def test_regresja_goldow_30min():
    """Replay 14 dni: dokładnie znane zdarzenia, właściwe klasy (zamrożona regresja goldów)."""
    from app.core_gpon import c_detect as CD, c_diagnose as DG
    inc, _ = CD.replay(RRD_PULL, rra_idx=5, debounce_slots=1, verbose=False)
    ev = DG.diagnose(inc)
    klasy = {e["time_window"]["start_utc"][:10]: e["diagnosis"]["class"] for e in ev}
    assert klasy.get("2026-05-26") == "outage_upstream_or_opl"     # gold 4-OLT Orange
    assert klasy.get("2026-06-02") == "power_or_node"              # B06 power węzła
    assert klasy.get("2026-05-30") == "power_area_customers"       # prąd u klientów
