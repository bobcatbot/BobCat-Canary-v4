"""Per-guild message translation table.

Language files live in Languages/<code>.json at the repo root (e.g.
Languages/en-GB.json), each shaped as nested objects keyed by dotted path
("coinflip.tails", "coinflip.dashboard.options.foo" - any depth). The
<code> in the filename must be a real Discord locale code (Discord's own
fixed list - "en-GB", "es-ES", "de", etc.), not an arbitrary language tag,
because localizations() feeds those same codes straight to Discord's
name_localizations/description_localizations.

A guild's language comes from settings.language on its guild doc, read the
same sync way as style()/datetimes() below - no dashboard field/UI for it
yet, so every guild currently falls back to DEFAULT_LANG. A missing key
falls back to DEFAULT_LANG's copy, then to the dotted key itself as a
visible placeholder instead of raising, so an untranslated string shows up
in chat rather than crashing the command.
"""
import os
import json
from pathlib import Path
from typing import Any

DEFAULT_LANG = "en-GB"

_LANGUAGES_DIR = Path(__file__).resolve().parent.parent / "Languages"

class Translate:
    def __init__(self):
        self.translation = {}
        for filename in os.listdir(_LANGUAGES_DIR):
            if filename.endswith(".json"):
                with open(_LANGUAGES_DIR / filename, encoding="utf-8") as f:
                    self.translation[filename[:-5]] = json.load(f)

    def _language_for(self, guild) -> str:
        if guild is None:
            return DEFAULT_LANG

        from modules import bot as v  # deferred: bot.py imports this module, so importing bot at module level here would be circular
        guild_id = str(getattr(guild, "id", guild))
        data = v._sync_guilds.find_one({"_id": guild_id}, {"settings.language": 1})
        return ((data or {}).get("settings") or {}).get("language") or DEFAULT_LANG

    def _walk(self, lang: str, key: str) -> Any:
        node: Any = self.translation.get(lang)
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                return None
            node = node[part]
        return node

    def msg(self, guild, key: str, /, **kwargs) -> str:
        # guild and key are positional-only (the trailing `/`) specifically so
        # a JSON template CAN use {guild} (or {key}) as a placeholder name -
        # e.g. v.t.msg(ctx.guild, "x.y", guild="Server Name") - without it
        # colliding with these params. Without `/`, that call would raise
        # "got multiple values for argument 'guild'" the moment a template
        # needed a guild-name placeholder.
        language = self._language_for(guild)
        for lang in (language, DEFAULT_LANG):
            text = self._walk(lang, key)
            if isinstance(text, str):
                return text.format_map(kwargs) if kwargs else text
        return key

    def choices(self, guild, key: str, /) -> list:
        """Same fallback chain as msg(), but for a list of strings (e.g. a
        pool of random reply lines) instead of a single string."""
        language = self._language_for(guild)
        for lang in (language, DEFAULT_LANG):
            values = self._walk(lang, key)
            if isinstance(values, list):
                return values
        return [key]

    def table(self, guild, key: str, /) -> dict:
        """Same idea as msg()/choices(), but for an ordered {sub_key: text}
        mapping (e.g. a help category's list of command descriptions).
        Falls back per-entry rather than per-table, so a partially
        translated table still uses the guild's language for every key it
        has and only borrows DEFAULT_LANG for the ones it's missing - order
        follows DEFAULT_LANG since that's always the complete set."""
        default_table = self._walk(DEFAULT_LANG, key)
        if not isinstance(default_table, dict):
            return {}
        language = self._language_for(guild)
        if language == DEFAULT_LANG:
            return default_table
        guild_table = self._walk(language, key)
        guild_table = guild_table if isinstance(guild_table, dict) else {}
        return {k: guild_table.get(k, v) for k, v in default_table.items()}

    def localizations(self, key: str) -> dict:
        """Build a Discord name_localizations/description_localizations dict
        for a slash command decorator: {locale_code: text} for every loaded
        language that has this key, keyed by the same Discord locale codes
        used as the Languages/ filenames. Discord only needs the non-default
        locales, but including DEFAULT_LANG is harmless."""
        result = {}
        for lang in self.translation:
            text = self._walk(lang, key)
            if isinstance(text, str):
                result[lang] = text
        return result
