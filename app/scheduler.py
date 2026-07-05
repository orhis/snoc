# -*- coding: utf-8 -*-
"""
scheduler — serwis detektora (T3): pętla co SNOC_SCAN_INTERVAL (domyślnie 300 s = SLA 10 min
z polityki D5: zgasło → potwierdzenie po 2 slotach) wołająca pipeline rdzenia z rejestrem DB.

Uruchamiany przez compose jako osobny serwis: `python -m app.scheduler` (obok serwisu web).
Przed każdym przebiegiem nakłada progi polityki ze SettingsStore (edytowalne z panelu, T4).
Błędy przebiegu NIE zabijają pętli (log + kolejna iteracja).
"""
from __future__ import annotations

import os
import sys
import time
import traceback
from datetime import datetime

from .core_gpon import pipeline
from .db import get_db, get_settings_store
from .services import registry_service
from .services.policy import apply_settings

INTERVAL_S = int(os.environ.get("SNOC_SCAN_INTERVAL", "300"))


def run_once() -> None:
    active = apply_settings(get_settings_store())
    print(f"[scheduler] {datetime.now():%Y-%m-%d %H:%M:%S} progi: {active}")
    pipeline.main(registry=registry_service)


def main() -> None:
    print(f"[scheduler] start, interwał {INTERVAL_S}s (SNOC_SCAN_INTERVAL)")
    get_db()  # fail-fast: baza musi wstać zanim wejdziemy w pętlę
    while True:
        t0 = time.monotonic()
        try:
            run_once()
        except Exception:
            print("[scheduler] BŁĄD przebiegu (pętla żyje):", file=sys.stderr)
            traceback.print_exc()
        time.sleep(max(5.0, INTERVAL_S - (time.monotonic() - t0)))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
