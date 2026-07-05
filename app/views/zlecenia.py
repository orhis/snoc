# -*- coding: utf-8 -*-
"""Widok „Zlecenia" — WorkOrder: robota dla technika (status, przypisanie, notatki z terenu)."""
from __future__ import annotations

import streamlit as st
from sqlalchemy import select

from ..db import get_db
from ..models import WorkOrder
from .common import WO_STATUS, WO_TYPES


def render(session) -> None:
    st.title("🛠 Zlecenia")
    db = get_db()
    with db.session() as s:
        rows = list(s.execute(select(WorkOrder).order_by(WorkOrder.created_at.desc())).scalars())
        for r in rows:
            s.expunge(r)
    if not rows:
        st.info("Brak zleceń — tworzysz je z karty awarii (Zdarzenia → Zlecenie dla technika).")
        return
    for w in rows:
        with st.expander(f"**{w.number}** · {w.work_type} · {w.status}"
                         f"{' · ' + w.assigned_to if w.assigned_to else ''} · awaria: {w.outage_id or '—'}"):
            st.markdown(f"**Miejsce:** {w.location or '—'}")
            with st.form(f"wo_{w.id}"):
                c1, c2, c3 = st.columns(3)
                status = c1.selectbox("Status", WO_STATUS, index=WO_STATUS.index(w.status))
                wtype = c2.selectbox("Typ", WO_TYPES, index=WO_TYPES.index(w.work_type))
                assigned = c3.text_input("Przypisane do", value=w.assigned_to)
                notes = st.text_area("Notatki z roboty (co zastano/zrobiono)", value=w.work_notes)
                if st.form_submit_button("Zapisz"):
                    with db.session() as s:
                        obj = s.get(WorkOrder, w.id)
                        obj.status, obj.work_type = status, wtype
                        obj.assigned_to, obj.work_notes = assigned, notes
                        s.commit()
                    st.success("Zapisano.")
                    st.rerun()
