# -*- coding: utf-8 -*-
"""Wspólne dla widoków: opisy klas po ludzku, coverage słownie (przeniesione z dashboardu realtime)."""
from __future__ import annotations

KLASA = {  # klasa -> (ikona, opis po ludzku)
    "outage_upstream_or_opl": ("🔴", "Awaria u operatora nadrzędnego — kilka naszych węzłów zniknęło w tej samej chwili"),
    "power_or_node": ("🟠", "Padł nasz węzeł (zasilanie/OLT) — brak odpytu całego węzła"),
    "gpon_port": ("🟠", "Pełny pad portu GPON — problem w szafie (wkładka/patchcord), nie w polu"),
    "splitter_or_branch": ("🟡", "Częściowy pad za wspólnym elementem — uszkodzenie w polu za wskazanym punktem"),
    "power_area_customers": ("🔵", "Brak prądu U KLIENTÓW (plama sąsiednich słupków) — to nie nasza awaria"),
    "planned_maintenance": ("⚪", "Okno pracy planowej Orange/EPIX — nie eskalować"),
    "uncertain": ("⚫", "Sygnał niejednoznaczny — obserwacja, bez eskalacji"),
}

STATUS_OUTAGE = ["ACTIVE", "RESOLVED", "CLOSED"]
WO_TYPES = ["SERVICE", "INSPECTION", "CONSTRUCTION", "SUPERVISION", "ESTIMATION"]
WO_STATUS = ["NEW", "ASSIGNED", "IN_PROGRESS", "WAITING_FOR_CLIENT", "COMPLETED", "CLOSED", "REOPENED", "CANCELLED"]


def cov_opis(cov) -> str:
    try:
        c = float(cov)
    except (TypeError, ValueError):
        return "—"
    if c >= 0.9:
        return f"{c:.0%} — za wspólnym punktem zgasło (prawie) WSZYSTKO → awaria dokładnie tam"
    if c >= 0.5:
        return f"{c:.0%} — większość za wspólnym punktem zgasła → przyczyna tam lub tuż niżej"
    if c >= 0.2:
        return f"{c:.0%} — tylko część → plama (prąd?) albo przyczyna niżej"
    return f"{c:.0%} — rozproszone → wspólny punkt raczej przypadkowy (przyczyna poza kablem)"


def syg_opis(sig: str) -> str:
    return ("węzeł przestał odpowiadać (problem PRZED klientami: transport/zasilanie/OLT)"
            if "NaN" in str(sig)
            else "OLT odpytał, brak światła od klientów (problem ZA węzłem: pole / prąd u klientów)")
