"""
Wpięcia modułów usługowych FAM — ZAKOMENTOWANE wzorce. Odkomentuj i
dostosuj te, których używasz. Pakiety są już w requirements.txt.
(Wygenerowane przez fam new — wybrane moduły: email, audit, scheduler.)
"""

# === email / SMTP (odkomentuj) ===
# from fam_email import SmtpConfig, send_email, smtp_config_from_env
# cfg = smtp_config_from_env()                         # albo SmtpConfig(host=..., user=..., password=...)
# ok, detail = send_email(cfg, "Temat", "Treść", to=["a@b.pl"])

# === audit (odkomentuj, by włączyć) ===
# from fam_audit import AuditLogger
# from app.db import get_db
# _audit = AuditLogger(get_db()); _audit.ensure_schema()
# _audit.log("admin", "login_ok", ip="...")          # zapis akcji

# === scheduler (osobny serwis: app/scheduler.py + serwis w docker-compose) ===
# from fam_scheduler import DailyScheduler
# from fam_config_db import SettingsStore
# from app.db import get_db
# def job(today): ...                                  # Twoja logika dzienna
# DailyScheduler(job, store=SettingsStore(get_db()), run_hour=8).loop()
# Wygeneruj compose ze schedulerem: fam-deploy --app-name snoc --with-scheduler
