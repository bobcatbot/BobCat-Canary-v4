"""Maintenance mode for the dashboard.

One Mongo doc holds the switch so it survives a restart (you'll usually flip it
on right before one); it's mirrored in memory so the per-request check in
index.py costs nothing. The bot and dashboard share a process, so a change made
by `/dev maintenance` is live on the very next request.
"""
from modules.models import Maintenance

_DOC_ID = "maintenance"

_state = {"loaded": False, "enabled": False, "eta": None}

async def get_state() -> dict:
    """{'enabled': bool, 'eta': str | None}. Reads Mongo once, then memory."""
    if not _state["loaded"]:
        doc = await Maintenance.get(_DOC_ID)
        _state.update(loaded=True, enabled=bool(doc and doc.enabled), eta=doc.eta if doc else None)
    return _state

async def set_state(enabled: bool, eta: str | None = None, by: int | None = None) -> None:
    doc = await Maintenance.get(_DOC_ID) or Maintenance(id=_DOC_ID)
    doc.enabled, doc.eta, doc.updated_by = enabled, eta, str(by) if by else None
    await doc.save()
    _state.update(loaded=True, enabled=enabled, eta=eta)
