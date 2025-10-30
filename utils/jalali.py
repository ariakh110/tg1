"""Small Jalali datetime helpers using the `jdatetime` package.

This module provides small, well-documented functions to convert between
Python's native `datetime.datetime` and `jdatetime.datetime`, and to
format Jalali datetimes for display.

Install:
    pip install jdatetime

Usage examples:
    from tg1.utils.jalali import to_jalali, to_gregorian, format_jalali

    j = to_jalali(datetime.utcnow())
    s = format_jalali(j, "%Y/%m/%d %H:%M")
    g = to_gregorian(j)
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Union

try:
    import jdatetime
except Exception:  # pragma: no cover - optional dependency
    jdatetime = None


def jdatetime_available() -> bool:
    """Return True when the `jdatetime` package is importable."""
    return jdatetime is not None


def to_jalali(dt: Optional[datetime]) -> Optional[object]:
    """Convert a native datetime.datetime to jdatetime.datetime.

    - If `dt` is None -> returns None.
    - If `jdatetime` is not installed -> returns None (caller can fall back).
    - If `dt` is already a jdatetime.datetime -> returned as-is.
    - On conversion error -> returns None.
    """
    if dt is None:
        return None
    if jdatetime is None:
        return None
    # Already a jdatetime instance
    if isinstance(dt, getattr(jdatetime, "datetime")):
        return dt
    # Only convert real datetimes
    if isinstance(dt, datetime):
        try:
            return jdatetime.datetime.fromgregorian(datetime=dt)
        except Exception:
            return None
    return None


def to_gregorian(value: Optional[object]) -> Optional[datetime]:
    """Convert a jdatetime.datetime to a native datetime.datetime for DB/storage.

    - If value is None -> None
    - If value is a jdatetime.datetime -> return .togregorian()
    - If it's already a datetime.datetime -> returned as-is
    - Otherwise -> None
    """
    if value is None:
        return None
    # jdatetime not installed => accept only datetime
    if jdatetime is None:
        return value if isinstance(value, datetime) else None
    # jdatetime instance
    if isinstance(value, getattr(jdatetime, "datetime")):
        try:
            return value.togregorian()
        except Exception:
            return None
    # native datetime
    if isinstance(value, datetime):
        return value
    return None


def format_jalali(value: Optional[object], fmt: str = "%Y/%m/%d %H:%M") -> Optional[str]:
    """Return a formatted Jalali date/time string.

    If `value` is a native datetime, it will be converted to jdatetime first
    (if `jdatetime` is installed). Returns None on failure or when the
    jdatetime package is unavailable.
    """
    j = None
    if value is None:
        return None
    if jdatetime is None:
        # Optionally, you could format the gregorian dt here, but the caller
        # explicitly asked for Jalali formatting; return None to signal that
        # a conversion isn't available.
        return None
    # If value is already jdatetime
    if isinstance(value, getattr(jdatetime, "datetime")):
        j = value
    else:
        # try to convert native datetime to jdatetime
        if isinstance(value, datetime):
            try:
                j = jdatetime.datetime.fromgregorian(datetime=value)
            except Exception:
                return None
        else:
            return None

    try:
        return j.strftime(fmt)
    except Exception:
        return None


__all__ = [
    "jdatetime_available",
    "to_jalali",
    "to_gregorian",
    "format_jalali",
]
