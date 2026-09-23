"""Dashboard translations: same Languages/*.json and engine as the bot, but the
language is the *viewer's*, not the guild's - the settings card changes what
the bot says in a server, not what an admin reads on the dashboard.

Viewer language, in order: their Discord locale (stored on the session at
login), then their browser's Accept-Language, then DEFAULT_LANG. Dashboard
strings live under the top-level "dashboard" key in Languages/<code>.json.
"""
from quart import g, request, session
from modules import bot as v


def viewer_lang() -> str:
    lang = getattr(g, "_viewer_lang", None)
    if lang is None:
        discord_locale = (session.get("user") or {}).get("locale")
        browser = request.accept_languages.values() if request else []
        lang = v.t.resolve_locale(discord_locale, *browser)
        g._viewer_lang = lang
    return lang


def tr(key: str, /, **kwargs) -> str:
    """Translate a dashboard key for the current viewer (templates get this as t())."""
    return v.t.msg_lang(viewer_lang(), key, **kwargs)
