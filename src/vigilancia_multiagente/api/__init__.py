"""HTTP API package."""

import logging
import os

from vigilancia_multiagente.config.settings import get_settings

settings = get_settings()
audit_logger = logging.getLogger("vigilancia.audit")

if settings.audit_mode:
    os.makedirs("logs", exist_ok=True)
    _handler = logging.FileHandler("logs/audit.log")
    _handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    audit_logger.addHandler(_handler)
    audit_logger.setLevel(logging.DEBUG)
else:
    audit_logger.addHandler(logging.NullHandler())
