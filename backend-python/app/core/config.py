"""Compatibility shim for legacy imports.

This module keeps `app.core.config` import path working while canonical
settings now live in `app.config`.
"""

from app.config import Settings, get_settings, settings

__all__ = ["Settings", "get_settings", "settings"]
