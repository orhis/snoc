# -*- coding: utf-8 -*-
"""
paths — konfiguracja rdzenia domenowego GPON (odpowiednik config.py z realtime/).
Czyta zmienne środowiskowe (ładowane z .env przez app.settings przy starcie panelu;
w trybie CLI/scheduler ładujemy .env tutaj), defaulty wskazują na data/ w repo.
Rdzeń = stdlib only (decyzja D3).
"""
import os

_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # app/
_ROOT = os.path.dirname(_APP_DIR)                                        # repo root

def _load_env():
    p = os.path.join(_ROOT, ".env")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
_load_env()

def get(name, default=None):
    return os.environ.get(name, default)

_DATA = get("SNOC_DATA_DIR", os.path.join(_ROOT, "data"))

# --- artefakty wejściowe (kopiowane przy deployu; patrz data/README.md) ---
TOPO_DIR  = get("SNOC_TOPO_DIR",  os.path.join(_DATA, "topo"))
KLUCZ_CSV = get("SNOC_KLUCZ_CSV", os.path.join(_DATA, "klucz", "klucz_polaczony_enriched.csv"))
PP_CSV    = get("SNOC_PP_CSV",    os.path.join(_DATA, "pp", "pp_opl_v2.csv"))
EVLOG_CSV = get("SNOC_EVLOG_CSV", os.path.join(_DATA, "eventlog", "_all_eventlog.csv"))

# --- źródło RRD: PROD = katalog rra/ Cacti; DEV = folder pulla ---
RRD_DIR   = get("SNOC_RRD_DIR", "")
RRD_PULLS = get("SNOC_RRD_PULLS", r"F:/BRT/00.Informatyka_II_stopień/mgr/02_dane/raw")

# --- wyjścia (rejestr/zdarzenia/raporty) ---
DATA_DIR = get("SNOC_OUT_DIR", os.path.join(_DATA, "out"))

# --- polityka detekcji (decyzja D5; edytowalne docelowo z panelu — T4) ---
MIN_CLUSTER    = int(get("SNOC_MIN_CLUSTER", "2"))
DEBOUNCE_SLOTS = int(get("SNOC_DEBOUNCE", "2"))
COV_THRESHOLD  = float(get("SNOC_COV", "0.5"))
BATERIE_MIN    = int(get("SNOC_BATERIE_MIN", "50"))
IMPACT_ONT     = int(get("SNOC_IMPACT_ONT", "15"))

def registry_csv():   return os.path.join(DATA_DIR, "incident_registry.csv")
def registry_jsonl(): return os.path.join(DATA_DIR, "incident_registry.jsonl")
def zdarzenia_dir():  return os.path.join(DATA_DIR, "zdarzenia")
