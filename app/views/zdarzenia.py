# -*- coding: utf-8 -*-
"""Widok „Zdarzenia" — lista kart awarii + PANEL DOWODÓW (9 sekcji) + werdykt + akcje."""
from __future__ import annotations

import json
import datetime as dt

import streamlit as st
from sqlalchemy import select

from ..db import get_db
from ..models import AIContext, MassOutage, WorkOrder
from ..services import registry_service
from .common import KLASA, STATUS_OUTAGE, cov_opis, syg_opis


def _pp_panel(start_utc: str) -> str:
    """Przejrzystość PP: wynik + 2 najbliższe okna (żeby było widać, że dane są realne)."""
    from ..core_gpon import pp_suppression as PP
    try:
        t0 = dt.datetime.fromisoformat(str(start_utc)[:19])
    except ValueError:
        return "nie sprawdzono (zły format czasu)"
    try:
        pp = PP.load_pp()
    except FileNotFoundError:
        return "brak artefaktu data/pp (patrz data/README.md)"
    chk = PP.check(t0, pp=pp)
    near = sorted(pp, key=lambda p: abs((p["start_utc"] - t0).total_seconds()))[:2]
    out = ["⛔ zdarzenie W OKNIE pracy planowej" if chk["suppressed"]
           else f"✅ żadne z {len(pp)} okien PP nie pokrywa zdarzenia"]
    for p in near:
        dh = (p["start_utc"] - t0).total_seconds() / 3600
        out.append(f"- najbliższe PP {p['pp_id']}: {p['start_utc']:%Y-%m-%d %H:%M}–{p['end_utc']:%H:%M} UTC "
                   f"({dh:+.0f} h) — {p['subject'][:60]}")
    return "\n".join(out)


def _confirm_txt(ev: dict) -> str:
    c = ev.get("confirmation_librenms", {})
    s = c.get("status")
    if s == "confirmed":
        return (f"✅ potwierdzone: {c.get('n_devices')} urządzeń down "
                f"(pierwszy {str(c.get('first_down_utc'))[:19]} UTC, powrót {str(c.get('recovery_utc'))[:19]})\n\n"
                f"urządzenia: {', '.join(c.get('devices', [])[:8])}")
    if s == "not_confirmed":
        return "➖ brak Device-Down w LibreNMS — przy sygnaturze LOS-pole spójne (węzeł żył)"
    if s == "no_coverage":
        return "⬜ eventlog nie pokrywa okresu — brak pokrycia ≠ brak zdarzenia (D6)"
    return "⬜ nie sprawdzano"


def _karta(m: MassOutage, user: str) -> None:
    ev = json.loads(m.model_dowodow) if m.model_dowodow else {}
    ik, opis = KLASA.get(m.klasa, ("❓", m.klasa))
    with st.expander(f"{ik} **{m.started_at[:16]}** · {m.klasa} · {m.olts} · ONT: {m.n_onts} "
                     f"· status: {m.status}" + (f" · 🔁 recydywa ×{m.recydywa_element}" if m.recydywa_element else "")):
        st.caption(opis)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**1. Sygnatura:** `{m.sygnatura}`\n\n{syg_opis(m.sygnatura)}")
            st.markdown(f"**2. Zakres:** OLT `{m.olts}` · **{m.n_onts} ONT**")
            st.markdown(f"**3. Wskazanie na mapie:** `{m.common_element or '—'}`\n\n"
                        f"pokrycie: {cov_opis(m.coverage)}")
            ti = ev.get("topology_inference", {})
            if str(ti.get("cannot_resolve_below")).lower() == "true":
                st.caption("⚠️ mapa kończy się na słupku — niżej (splitter/przyłącze) system się nie wypowiada")
        with c2:
            st.markdown("**4. Prace planowe (kontrola):**\n\n" + _pp_panel(m.started_at))
            st.markdown("**5. Drugie źródło (LibreNMS):**\n\n" + _confirm_txt(ev))
            st.markdown(f"**6. Diagnoza:** {m.klasa} (pewność {m.confidence}) · taksonomia: {m.taksonomia_mgr}")
        st.markdown(f"**7. Rekomendacja:** {m.recommended_action}")
        st.caption(f"9. Zamrożone dowody: `{m.evidence_dir}`")

        # --- 8. werdykt operatora -> AIContext (gold-data) ---
        db = get_db()
        with db.session() as s:
            verdicts = list(s.execute(select(AIContext).where(AIContext.outage_id == m.id)
                                      .order_by(AIContext.created_at)).scalars())
        if verdicts:
            st.markdown("**Dotychczasowe decyzje:**")
            for v in verdicts:
                st.markdown(f"- `{v.created_at:%m-%d %H:%M}` **{v.decision}** ({v.created_by}): {v.reasoning}")
        with st.form(f"verdict_{m.id}"):
            d1, d2 = st.columns([1, 2])
            decision = d1.selectbox("Werdykt", ["potwierdzam", "falszywka", "inna_klasa", "obserwowac"],
                                    key=f"dec_{m.id}")
            reasoning = d2.text_input("Uzasadnienie (WYMAGANE — to dane pod agenta)", key=f"rea_{m.id}")
            if st.form_submit_button("Zapisz werdykt"):
                try:
                    registry_service.add_verdict(m.id, decision, reasoning, user=user)
                    st.success("Zapisano do dziennika decyzji (AIContext).")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

        # --- akcje: status + zlecenie dla technika ---
        a1, a2, a3 = st.columns(3)
        new_status = a1.selectbox("Status karty", STATUS_OUTAGE,
                                  index=STATUS_OUTAGE.index(m.status), key=f"st_{m.id}")
        if a1.button("Zmień status", key=f"stb_{m.id}") and new_status != m.status:
            with db.session() as s:
                obj = s.get(MassOutage, m.id)
                obj.status = new_status
                if new_status in ("RESOLVED", "CLOSED") and not obj.ended_at:
                    obj.ended_at = dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                s.commit()
            st.rerun()
        if a2.button("➕ Zlecenie dla technika", key=f"wo_{m.id}"):
            with db.session() as s:
                n = s.query(WorkOrder).count() + 1
                s.add(WorkOrder(number=f"SNOC-WO-{n:04d}", outage_id=m.id, work_type="SERVICE",
                                location=f"{m.common_element} | {m.affected_area}",
                                created_by=user))
                s.commit()
            st.success("Utworzono zlecenie (zakładka Zlecenia).")


def render(session) -> None:
    st.title("🚨 Zdarzenia")
    db = get_db()
    with db.session() as s:
        rows = list(s.execute(select(MassOutage).order_by(MassOutage.started_at.desc())).scalars())
        # detach: czytamy pola po zamknięciu sesji
        for r in rows:
            s.expunge(r)
    f1, f2 = st.columns(2)
    st_filter = f1.multiselect("Status", STATUS_OUTAGE, default=["ACTIVE"])
    show_obs = f2.checkbox("pokaż też obserwacje (uncertain)", value=False)
    for m in rows:
        if st_filter and m.status not in st_filter:
            continue
        if not show_obs and m.klasa == "uncertain":
            continue
        _karta(m, user=session.display_name)
    if not rows:
        st.info("Brak kart. Uruchom detektor: `python -m app.scheduler` (lub jednorazowo pipeline).")
