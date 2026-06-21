"""Central logging configuration.

Console + rotating file handler (logs/backend.log). Frontend logs arrive via the
/logs/client endpoint and are written through the "frontend" logger into the same
file, so backend + frontend events sit in one timeline.
"""
import logging
import logging.handlers
import os
import sys

from backend.app.core.config import settings

LOG_DIR = os.path.join(os.getcwd(), "logs")
LOG_FILE = os.path.join(LOG_DIR, "backend.log")

_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"

_configured = False


def setup_logging() -> None:
    global _configured
    if _configured:
        return

    os.makedirs(LOG_DIR, exist_ok=True)
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    formatter = logging.Formatter(_FORMAT, datefmt=_DATEFMT)

    # Console handler (UTF-8 so Cyrillic isn't mangled on Windows consoles).
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # py3.7+
    except Exception:  # noqa: BLE001
        pass

    # Rotating file handler: 5 files × 5 MB.
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    # Drop pre-existing handlers (uvicorn/basicConfig) to avoid duplicates.
    root.handlers.clear()
    root.addHandler(console)
    root.addHandler(file_handler)

    # Align uvicorn loggers with our handlers.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.propagate = True

    logging.getLogger(__name__).info("Logging configured → %s (level=%s)", LOG_FILE, settings.LOG_LEVEL)
    _configured = True


# Dedicated logger for client (frontend) events.
frontend_logger = logging.getLogger("frontend")
