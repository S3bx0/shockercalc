"""Bezpieczny most z Pythona do Firebase Analytics i Crashlytics na Androidzie."""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import traceback
from typing import Mapping, Optional


log = logging.getLogger(__name__)
_EVENT_RE = re.compile(r"[^a-zA-Z0-9_]")


def _activity():
    if "ANDROID_ARGUMENT" not in os.environ:
        return None
    try:
        from jnius import autoclass, cast

        base = autoclass("org.kivy.android.PythonActivity").mActivity
        return cast(
            "pl.smilczarek.refrigerationcalc.RefrigerationCalcActivity",
            base,
        )
    except Exception:
        log.debug("Firebase activity bridge unavailable", exc_info=True)
        return None


def is_available() -> bool:
    activity = _activity()
    if activity is None:
        return False
    try:
        return bool(activity.isFirebaseTelemetryAvailable())
    except Exception:
        return False


def has_preference() -> bool:
    activity = _activity()
    if activity is None:
        return True
    try:
        return bool(activity.hasTelemetryPreference())
    except Exception:
        return True


def is_enabled() -> bool:
    activity = _activity()
    if activity is None:
        return False
    try:
        return bool(activity.isTelemetryEnabled())
    except Exception:
        return False


def set_enabled(enabled: bool) -> bool:
    activity = _activity()
    if activity is None:
        return False
    try:
        activity.setTelemetryEnabled(bool(enabled))
        return True
    except Exception:
        log.debug("Unable to change Firebase telemetry", exc_info=True)
        return False


def log_event(name: str, parameters: Optional[Mapping[str, object]] = None) -> None:
    activity = _activity()
    if activity is None:
        return
    safe_name = _EVENT_RE.sub("_", str(name or "event"))[:40]
    safe_parameters = {}
    for key, value in (parameters or {}).items():
        safe_key = _EVENT_RE.sub("_", str(key))[:40]
        if isinstance(value, bool):
            safe_parameters[safe_key] = int(value)
        elif isinstance(value, (int, float, str)):
            safe_parameters[safe_key] = value
    try:
        activity.logAnalyticsEvent(
            safe_name,
            json.dumps(safe_parameters, ensure_ascii=True),
        )
    except Exception:
        log.debug("Unable to log Firebase event", exc_info=True)


def set_screen(name: str) -> None:
    log_event(
        "screen_view",
        {"screen_name": str(name)[:80], "screen_class": "KivyScreen"},
    )


def remote_bool(key: str, fallback: bool = False) -> bool:
    activity = _activity()
    if activity is None:
        return fallback
    try:
        return bool(activity.getRemoteConfigBoolean(str(key), bool(fallback)))
    except Exception:
        return fallback


def remote_int(key: str, fallback: int) -> int:
    activity = _activity()
    if activity is None:
        return int(fallback)
    try:
        return int(activity.getRemoteConfigLong(str(key), int(fallback)))
    except Exception:
        return int(fallback)


def record_exception(exc: BaseException, context: str = "python") -> None:
    activity = _activity()
    if activity is None:
        return
    stack = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    try:
        activity.recordPythonException(
            str(context)[:80],
            type(exc).__name__[:80],
            str(exc)[:500],
            stack[-8000:],
        )
    except Exception:
        log.debug("Unable to report Python exception", exc_info=True)


def install_exception_hook() -> None:
    """Raportuje nieobsluzone wyjatki Pythona bez zmiany ich obslugi."""
    previous = sys.excepthook
    if getattr(previous, "_refrigeration_telemetry_hook", False):
        return

    def _hook(exc_type, exc, tb):
        try:
            record_exception(exc, "uncaught_python")
        finally:
            previous(exc_type, exc, tb)

    _hook._refrigeration_telemetry_hook = True
    sys.excepthook = _hook
