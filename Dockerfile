# snoc — multi-stage build. Wygenerowane przez FAM (modules/deploy).
# Builder kompiluje deps, runtime bierze tylko artefakty (mniejszy, czystszy image).
# Deploy: Synology Container Manager za VPN/LAN. Hardening = defense in depth.

# =========================================================================
# Stage 1: BUILDER — kompilacja zależności w izolacji
# =========================================================================
FROM python:3.11-slim-bookworm AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
# Najpierw tylko requirements — layer cache rebuilduje deps gdy plik się zmieni
# (kod aplikacji ma osobny layer, częściej się zmienia).
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# =========================================================================
# Stage 2: RUNTIME — slim image bez build tools
# =========================================================================
FROM python:3.11-slim-bookworm AS runtime

# (brak runtime apt — czysty python:slim wystarcza)

# Non-root user — exploit w apce nie dostanie root. UID 1000 pasuje do bind
# mount data/ na Synology (user hosta).
RUN groupadd --system --gid 1000 snoc \
    && useradd --system --uid 1000 --gid snoc --create-home --shell /sbin/nologin snoc

COPY --from=builder /install /usr/local

WORKDIR /app

COPY --chown=snoc:snoc app/ ./app/
COPY --chown=snoc:snoc .streamlit/ ./.streamlit/
COPY --chown=snoc:snoc scripts/ ./scripts/

# Katalog na dane (bind mount overlay'uje read-only rootfs).
RUN mkdir -p /app/data && chown snoc:snoc /app/data

USER snoc

# Streamlit config przez env (czytelniej niż CLI flagi).
# SERVER_ADDRESS=0.0.0.0 MUSI być — inaczej bind tylko 127.0.0.1 i port mapping nie działa.
ENV STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

EXPOSE 8501

# Healthcheck — Container Manager zrestartuje gdy /_stcore/health milczy.
# start-period 30s bo init (PBKDF2/DB) bywa wolny na słabym NAS.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health', timeout=3).read()" || exit 1

CMD ["streamlit", "run", "app/streamlit_app.py"]
