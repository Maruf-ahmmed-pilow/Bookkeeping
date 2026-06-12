"""Centralised logging configuration.

Call :func:`configure_logging` once at application startup (and from the seed
script) so every module's ``logging.getLogger(__name__)`` shares a consistent
format and level. Importing this module has no side effects.
"""

from __future__ import annotations

import logging

from .config import settings

_LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
_configured = False


def configure_logging() -> None:
    """Initialise root logging from ``settings.log_level``.

    Idempotent: repeated calls are no-ops so importing modules or re-running the
    seed script never installs duplicate handlers.
    """
    global _configured
    if _configured:
        return

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(level=level, format=_LOG_FORMAT)
    _configured = True
