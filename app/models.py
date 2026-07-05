"""Modele apki (DeclarativeBase aplikacji). LoginAttempt dostarcza fam_auth
na własnym Base — tworzymy go obok w db.py."""

from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(128), default="")
    totp_secret: Mapped[str] = mapped_column(String(64), default="")  # 2FA (puste = wyłączone)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)


# ============================================================
# Modele NOC — schemat przeszczepiony z SOSDH bez multi-tenant (decyzja D2)
# ============================================================
from datetime import datetime, timezone
from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MassOutage(Base):
    """Karta awarii masowej (kontener). U nas tworzona AUTOMATYCZNIE przez detektor;
    started_at = czas wykrycia w danych (nie pierwszego telefonu — różnica vs SOSDH)."""
    __tablename__ = "mass_outages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)   # event_id "INC-YYYYMMDD-HHMM-olt"
    title: Mapped[str] = mapped_column(String(255), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    affected_area: Mapped[str] = mapped_column(Text, default="")     # element + OLT-y tekstowo

    started_at: Mapped[str] = mapped_column(String(32))              # UTC ISO (spójnie z core_gpon)
    started_at_override: Mapped[str] = mapped_column(String(32), default="")
    override_reason: Mapped[str] = mapped_column(Text, default="")
    ended_at: Mapped[str] = mapped_column(String(32), default="")
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE")  # ACTIVE/RESOLVED/CLOSED

    # --- diagnoza (strukturalnie; SOSDH trzymał w opisie) ---
    klasa: Mapped[str] = mapped_column(String(40), default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    sygnatura: Mapped[str] = mapped_column(String(40), default="")
    olts: Mapped[str] = mapped_column(String(255), default="")       # CSV nazw
    n_onts: Mapped[int] = mapped_column(Integer, default=0)
    common_element: Mapped[str] = mapped_column(String(64), default="")
    coverage: Mapped[float] = mapped_column(Float, default=0.0)
    taksonomia_mgr: Mapped[str] = mapped_column(String(64), default="")
    recommended_action: Mapped[str] = mapped_column(Text, default="")
    recydywa_element: Mapped[int] = mapped_column(Integer, default=0)
    evidence_dir: Mapped[str] = mapped_column(String(255), default="")  # zamrożone dowody (pliki!)
    model_dowodow: Mapped[str] = mapped_column(Text, default="")        # pełny JSON zdarzenia

    created_by: Mapped[str] = mapped_column(String(64), default="DETEKTOR")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)


class AIContext(Base):
    """Dziennik decyzji z uzasadnieniem = gold-data pod agenta (v1 zbieranie ->
    v1.5 AI sugeruje+człowiek zatwierdza -> v2 AI decyduje+nadzór). reasoning WYMAGANY."""
    __tablename__ = "ai_contexts"

    id: Mapped[int] = mapped_column(primary_key=True)
    outage_id: Mapped[str | None] = mapped_column(ForeignKey("mass_outages.id"), nullable=True, index=True)
    workorder_id: Mapped[int | None] = mapped_column(ForeignKey("work_orders.id"), nullable=True)

    action_type: Mapped[str] = mapped_column(String(16))   # DECISION/ESCALATION/RESOLUTION/ASSIGNMENT/VERDICT
    input_snapshot: Mapped[str] = mapped_column(Text, default="")   # JSON: stan W CHWILI decyzji
    decision: Mapped[str] = mapped_column(String(64))
    reasoning: Mapped[str] = mapped_column(Text)                    # WYMAGANE (walidacja w serwisie)
    time_to_decision_s: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    was_overridden: Mapped[bool] = mapped_column(Boolean, default=False)
    overridden_by: Mapped[str] = mapped_column(String(64), default="")
    override_reason: Mapped[str] = mapped_column(Text, default="")

    created_by: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class WorkOrder(Base):
    """Zlecenie roboty dla technika, podpięte pod awarię; miejsce = element z localize."""
    __tablename__ = "work_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(32), unique=True)     # SNOC-WO-0001
    work_type: Mapped[str] = mapped_column(String(16), default="SERVICE")
    status: Mapped[str] = mapped_column(String(24), default="NEW")
    outage_id: Mapped[str | None] = mapped_column(ForeignKey("mass_outages.id"), nullable=True, index=True)

    scheduled_start: Mapped[str] = mapped_column(String(32), default="")
    scheduled_end: Mapped[str] = mapped_column(String(32), default="")
    location: Mapped[str] = mapped_column(Text, default="")
    work_notes: Mapped[str] = mapped_column(Text, default="")

    created_by: Mapped[str] = mapped_column(String(64), default="")
    assigned_to: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
