# -*- coding: utf-8 -*-
"""Testy T2: rejestr na DB (MassOutage/AIContext) — kontrakt jak c_registry + reguły D2/D6."""
import json
import pytest


def _ev(eid="INC-20260601-1200-testolt", start="2026-06-01 12:00:00", klasa="splitter_or_branch",
        olts=("testolt",), element="PE/TEST/001"):
    return {
        "event_id": eid,
        "time_window": {"start_utc": start, "end_utc": "2026-06-01 13:00:00", "source": "t", "confidence": 0.9},
        "signal": {"value": "LOS_optyczny(-80000)", "sources": ["rrd"], "n_onts": 3, "confidence": 0.85},
        "affected_scope": {"olts": list(olts), "onts": 3, "hp": None, "sources": ["rrd"], "confidence": 0.8},
        "topology_inference": {"lowest_reliable_common_level": "PE", "common_element": element,
                               "coverage_ratio": 1.0, "provenance": "t", "cannot_resolve_below": True,
                               "missing_data": [], "confidence": 0.9},
        "diagnosis": {"class": klasa, "confidence": 0.8, "abstain": False,
                      "taksonomia_mgr": "5", "recommended_action": "test"},
    }


@pytest.fixture()
def svc(tmp_path, monkeypatch):
    """Świeża baza SQLite + wyjścia w tmp (nie ruszamy data/)."""
    from app import db as appdb
    from app.core_gpon import paths as cfg
    monkeypatch.setattr(appdb, "_db", None)
    monkeypatch.setattr(appdb, "build_db", lambda path="ignored": _mkdb(tmp_path))
    monkeypatch.setattr(cfg, "DATA_DIR", str(tmp_path / "out"))
    from app.services import registry_service as RS
    return RS


def _mkdb(tmp_path):
    from fam_config_db import Database
    from app.models import Base
    db = Database(str(tmp_path / "test.db"), Base)
    db.init()
    return db


def test_register_idempotencja_i_scalanie(svc):
    from app.models import MassOutage
    from app.db import get_db
    n, u = svc.register([_ev()])
    assert (n, u) == (1, 0)
    # re-run: to samo zdarzenie -> update, nie duplikat
    n, u = svc.register([_ev()])
    assert (n, u) == (0, 1)
    # re-diagnoza: INNA klasa + inny event_id, ale te same OLT-y i start ±1h -> SCALONE
    n, u = svc.register([_ev(eid="INC-20260601-1230-testolt", start="2026-06-01 12:30:00",
                             klasa="power_area_customers")])
    assert (n, u) == (0, 1)
    with get_db().session() as s:
        rows = s.query(MassOutage).all()
        assert len(rows) == 1
        assert rows[0].klasa == "power_area_customers"      # klasa zaktualizowana
        assert rows[0].id == "INC-20260601-1200-testolt"    # tożsamość karty zachowana


def test_recydywa_elementu(svc):
    from app.models import MassOutage
    from app.db import get_db
    svc.register([_ev()])
    svc.register([_ev(eid="INC-20260603-1200-testolt", start="2026-06-03 12:00:00")])  # ten sam element, 2 dni później
    with get_db().session() as s:
        rec = {m.id: m.recydywa_element for m in s.query(MassOutage)}
    assert rec["INC-20260601-1200-testolt"] == 0
    assert rec["INC-20260603-1200-testolt"] == 1


def test_verdict_wymaga_reasoning(svc):
    svc.register([_ev()])
    with pytest.raises(ValueError):
        svc.add_verdict("INC-20260601-1200-testolt", "potwierdzam", "   ", user="bart")
    svc.add_verdict("INC-20260601-1200-testolt", "potwierdzam", "koparka na Lipowej", user="bart")
    from app.models import AIContext
    from app.db import get_db
    with get_db().session() as s:
        ac = s.query(AIContext).one()
        assert ac.decision == "potwierdzam" and ac.created_by == "bart"
        assert json.loads(ac.input_snapshot)["event_id"] == "INC-20260601-1200-testolt"  # snapshot z chwili decyzji


def test_jsonl_dowodow_pisany(svc, tmp_path):
    import os
    from app.core_gpon import paths as cfg
    svc.register([_ev()])
    assert os.path.exists(cfg.registry_jsonl())
