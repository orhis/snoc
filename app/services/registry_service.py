# -*- coding: utf-8 -*-
"""
registry_service — rejestr zdarzeń na bazie (MassOutage/AIContext) zamiast CSV (T2, D2).
Kontrakt jak core_gpon.c_registry.register(events) — dzięki temu pipeline dostaje ten moduł
przez wstrzyknięcie (rdzeń domenowy pozostaje stdlib, bez zależności od SQLAlchemy — D3).

Zasady przeniesione z c_registry:
- scalanie: te same OLT-y + start w ±1 h = to samo zdarzenie (niezależnie od klasy — re-diagnoza
  nie dubluje karty),
- werdykty operatora (AIContext) NIGDY nie ruszane przy update,
- recydywa_element przeliczana globalnie (ile WCZEŚNIEJSZYCH kart na tym samym elemencie),
- pełne modele dowodów dodatkowo do JSONL (plik = dowód, D6).
"""
from __future__ import annotations

import json
import os
import datetime as dt

from sqlalchemy import select

from ..db import get_db
from ..models import AIContext, MassOutage
from ..core_gpon import paths as _cfg

TITLE = {  # klasa -> tytuł po ludzku (do listy w panelu)
    "outage_upstream_or_opl": "Awaria u operatora nadrzędnego (kilka węzłów naraz)",
    "power_or_node": "Węzeł nieosiągalny (zasilanie/OLT)",
    "gpon_port": "Pełny pad portu GPON (strona szafy)",
    "splitter_or_branch": "Awaria za wspólnym elementem w polu",
    "power_area_customers": "Brak prądu w obszarze u klientów (nie nasza sieć)",
    "planned_maintenance": "Okno pracy planowej",
    "uncertain": "Sygnał niejednoznaczny (obserwacja)",
}


def _ts(x: str) -> float:
    try:
        return dt.datetime.fromisoformat(str(x)).timestamp()
    except Exception:
        return 0.0


def _row_from_event(ev: dict) -> dict:
    d = ev["diagnosis"]; ti = ev["topology_inference"]; s = ev["affected_scope"]
    eid = ev["event_id"]
    return dict(
        id=eid,
        title=TITLE.get(d["class"], d["class"]),
        description=json.dumps(ev.get("confirmation_librenms", {}), ensure_ascii=False),
        affected_area=f"element={ti.get('common_element') or '—'}; OLT={','.join(s['olts'])}",
        started_at=ev["time_window"].get("start_utc_precise") or ev["time_window"]["start_utc"],
        ended_at=ev["time_window"]["end_utc"],
        klasa=d["class"], confidence=float(d.get("confidence") or 0),
        sygnatura=str(ev["signal"].get("value", "")),
        olts=",".join(s["olts"]), n_onts=int(s.get("onts") or 0),
        common_element=ti.get("common_element") or "",
        coverage=float(ti.get("coverage_ratio") or 0),
        taksonomia_mgr=str(d.get("taksonomia_mgr", "")),
        recommended_action=d.get("recommended_action", ""),
        evidence_dir=os.path.join(_cfg.zdarzenia_dir(), eid),
        model_dowodow=json.dumps(ev, ensure_ascii=False, default=str),
    )


def register(events: list[dict]):
    """Upsert zdarzeń do MassOutage. Zwraca (nowe, zaktualizowane) — kontrakt c_registry."""
    db = get_db()
    nowe = upd = 0
    with db.session() as ses:
        existing = list(ses.execute(select(MassOutage)).scalars())
        by_id = {m.id: m for m in existing}
        for ev in events:
            row = _row_from_event(ev)
            eid = row["id"]
            if eid not in by_id:  # scal: te same OLT-y + start ±1 h (klasa może się zmienić!)
                t0 = _ts(row["started_at"])
                for m in existing:
                    if m.olts == row["olts"] and abs(_ts(m.started_at) - t0) <= 3600:
                        eid = m.id
                        break
            if eid in by_id:
                m = by_id[eid]
                for k, v in row.items():
                    if k in ("id", "started_at_override", "override_reason"):
                        continue  # tożsamość + ręczne korekty nietykalne
                    setattr(m, k, v if k != "id" else m.id)
                upd += 1
            else:
                m = MassOutage(**row)
                ses.add(m)
                existing.append(m)
                by_id[eid] = m
                nowe += 1
        # recydywa: liczba WCZEŚNIEJSZYCH kart na tym samym elemencie
        seen: dict[str, int] = {}
        for m in sorted(existing, key=lambda x: x.started_at):
            el = m.common_element or ""
            m.recydywa_element = seen.get(el, 0) if el else 0
            if el:
                seen[el] = seen.get(el, 0) + 1
        ses.commit()
    # pełne modele dowodów do JSONL (plik = dowód, D6)
    os.makedirs(_cfg.DATA_DIR, exist_ok=True)
    with open(_cfg.registry_jsonl(), "a", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev, ensure_ascii=False, default=str) + "\n")
    return nowe, upd


def add_verdict(outage_id: str, decision: str, reasoning: str, user: str,
                action_type: str = "VERDICT", confidence: float = 0.0):
    """Werdykt operatora -> AIContext (gold-data). reasoning WYMAGANY (schemat SOSDH)."""
    if not (reasoning or "").strip():
        raise ValueError("reasoning jest wymagany — zapisz DLACZEGO (gold-data dla agenta)")
    db = get_db()
    with db.session() as ses:
        m = ses.get(MassOutage, outage_id)
        if m is None:
            raise ValueError(f"brak karty awarii {outage_id}")
        snap = m.model_dowodow  # stan W CHWILI decyzji
        ses.add(AIContext(outage_id=outage_id, action_type=action_type,
                          input_snapshot=snap, decision=decision, reasoning=reasoning,
                          confidence=confidence, created_by=user))
        ses.commit()
