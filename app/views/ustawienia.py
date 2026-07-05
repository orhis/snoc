# -*- coding: utf-8 -*-
"""Widok „Ustawienia" — progi polityki detekcji (D5) w SettingsStore.
Scheduler czyta je przed KAŻDYM przebiegiem — zmiana działa od następnego skanu (≤5 min)."""
from __future__ import annotations

import streamlit as st

from ..db import get_settings_store
from ..services.policy import KEYS, current


def render(session) -> None:
    st.title("⚙️ Ustawienia — polityka detekcji (D5)")
    if not session.is_admin:
        st.warning("Tylko admin zmienia progi.")
        return
    store = get_settings_store()
    vals = current(store)
    with st.form("policy"):
        new = {}
        for key, (attr, typ, label, help_) in KEYS.items():
            if typ is float:
                new[key] = st.number_input(label, value=float(vals[key]), step=0.05,
                                           format="%.2f", help=help_)
            else:
                new[key] = st.number_input(label, value=int(vals[key]), step=1, help=help_)
        if st.form_submit_button("Zapisz progi"):
            for key, v in new.items():
                store.set(key, str(v))
            st.success("Zapisano — scheduler zastosuje od następnego przebiegu (≤5 min).")
    st.caption("Pochodzenie progów i uzasadnienia: docs/decisions.md → D5. "
               "Kalibracja coverage: próg nieczuły w zakresie 0.3–0.7 (separacja incydenty≈1 vs szum <0.3).")
