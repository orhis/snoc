# -*- coding: utf-8 -*-
"""Testy T3: polityka ze SettingsStore + jedna iteracja schedulera (pipeline mockowany)."""
import pytest


@pytest.fixture()
def env(tmp_path, monkeypatch):
    from fam_config_db import Database, SettingsStore
    from app.models import Base
    from app import db as appdb
    db = Database(str(tmp_path / "t.db"), Base)
    db.init()
    monkeypatch.setattr(appdb, "_db", db)
    return db


def test_policy_apply_z_defaultow_i_store(env):
    from app.db import get_settings_store
    from app.services.policy import apply_settings, KEYS
    from app.core_gpon import paths as cfg
    store = get_settings_store()
    # bez wpisów -> defaulty z paths (D5)
    active = apply_settings(store)
    assert active["snoc.baterie_min"] == 50 and active["snoc.min_cluster"] == 2
    # wpis w store nadpisuje runtime
    store.set("snoc.cov_threshold", "0.7")
    active = apply_settings(store)
    assert active["snoc.cov_threshold"] == 0.7 and cfg.COV_THRESHOLD == 0.7
    assert set(active) == set(KEYS)


def test_scheduler_iteracja_wola_pipeline_z_rejestrem_db(env, monkeypatch):
    from app import scheduler
    from app.core_gpon import pipeline
    calls = {}
    monkeypatch.setattr(pipeline, "main", lambda registry=None, **kw: calls.setdefault("registry", registry))
    scheduler.run_once()
    from app.services import registry_service
    assert calls["registry"] is registry_service   # detektor pisze do DB, nie do CSV
