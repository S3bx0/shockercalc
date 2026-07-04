"""Entitlements-to-UI synchronization helpers."""
from __future__ import annotations

from tpof.mobile.entitlements import Entitlements


def _sync_module_ownership(entitlements: Entitlements, module_id: str, owned: bool) -> None:
    """Synchronizuje lokalne uprawnienie modułu z aktualnym stanem Google Play."""
    if owned:
        entitlements.grant_module(module_id)
    else:
        entitlements.revoke_module(module_id)
