# -*- coding: utf-8 -*-
"""
policy — progi polityki detekcji (D5) w SettingsStore, edytowalne z panelu (T4),
czytane przez scheduler przed KAŻDYM przebiegiem (T3). Defaulty = wartości z paths (env).
"""
from __future__ import annotations

from ..core_gpon import paths as _cfg

KEYS = {  # klucz w SettingsStore -> (atrybut w paths, typ, etykieta, pomoc)
    "snoc.min_cluster": ("MIN_CLUSTER", int, "Minimalny klaster (ONT)",
                         "1 zgaśnięcie = sprawa BOK; alarm od ILU ONT naraz (D5)"),
    "snoc.debounce_slots": ("DEBOUNCE_SLOTS", int, "Debounce (sloty 5-min)",
                            "2 = potwierdzenie po 10 min (zgasło→+5→+10; D5)"),
    "snoc.cov_threshold": ("COV_THRESHOLD", float, "Próg coverage",
                           "bliskość topologiczna klastra: 2/2 za słupkiem=1.0 (D5; kalibracja: nieczuły 0.3–0.7)"),
    "snoc.baterie_min": ("BATERIE_MIN", int, "Baterie siłowni (min)",
                         ">50 min zaniku = weryfikacja rachunków + Enea + agregat (D5)"),
    "snoc.impact_ont": ("IMPACT_ONT", int, "Duży impact (ONT)",
                        "od ilu ONT zdarzenie traktujemy jako duże (eskalacja/second-opinion)"),
}


def apply_settings(store) -> dict:
    """Nałóż wartości ze SettingsStore na paths (runtime). Zwraca aktywne wartości."""
    active = {}
    for key, (attr, typ, _, _) in KEYS.items():
        raw = store.get(key)
        val = typ(raw) if raw not in (None, "") else getattr(_cfg, attr)
        setattr(_cfg, attr, val)
        active[key] = val
    return active


def current(store) -> dict:
    return {key: (typ(store.get(key)) if store.get(key) not in (None, "") else getattr(_cfg, attr))
            for key, (attr, typ, _, _) in KEYS.items()}
