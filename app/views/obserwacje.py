# -*- coding: utf-8 -*-
"""Widok „Obserwacje" — uncertain (abstain) + recydywy: to, co się nie eskaluje, ale warto widzieć."""
from __future__ import annotations

import streamlit as st
from sqlalchemy import select

from ..db import get_db
from ..models import MassOutage


def render(session) -> None:
    st.title("👁 Obserwacje")
    db = get_db()
    with db.session() as s:
        rows = list(s.execute(select(MassOutage).order_by(MassOutage.started_at.desc())).scalars())
        for r in rows:
            s.expunge(r)
    unc = [m for m in rows if m.klasa == "uncertain"]
    rec = [m for m in rows if (m.recydywa_element or 0) > 0]
    st.subheader(f"Sygnały niejednoznaczne ({len(unc)}) — bez eskalacji")
    for m in unc:
        st.markdown(f"- `{m.started_at[:16]}` {m.olts} · element `{m.common_element}` · ONT {m.n_onts}")
    st.subheader(f"Recydywy elementów ({len(rec)}) — ten sam punkt choruje wielokrotnie")
    for m in sorted(rec, key=lambda x: -x.recydywa_element):
        st.markdown(f"- **×{m.recydywa_element + 1}** `{m.common_element}` — ostatnio {m.started_at[:16]} "
                    f"({m.klasa}, {m.olts})")
    if not unc and not rec:
        st.info("Pusto — nic do obserwowania.")
