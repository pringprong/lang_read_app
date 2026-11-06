"""Offline CC-CEDICT dictionary lookup (definitions plan §3, 2026-11-06).

Bundles the MDBG CC-CEDICT export (CC BY-SA 4.0) as a gzipped plain-text
resource. Entries look like:

    廚房 厨房 [chu2 fang2] /kitchen/CL:間|间[jian1]/

The app indexes entries by their **simplified** headword (the second field);
definitions are English, pinyin is converted to tone marks. The service is
strictly read-only after parsing and never raises — a missing or corrupt
file simply disables lookups so the app falls back to the translation model.
"""

from __future__ import annotations

import gzip
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path

from langread.app_config import resource_dir

logger = logging.getLogger(__name__)

ENV_CEDICT = "LANGREAD_CEDICT"  # path override; "off" disables the dictionary

CEDICT_GZ = resource_dir() / "dictionaries" / "cedict.txt.gz"

MAX_SENSES = 3
MAX_DEFINITION_CHARS = 200

_ENTRY_RE = re.compile(r"^(\S+)\s+(\S+)\s+\[([^\]]*)\]\s+/(.*)/\s*$")
_VARIANT_RE = re.compile(r"^(old )?variant of\b", re.IGNORECASE)

_TONE_MARKS = {
    "a": "āáǎà",
    "e": "ēéěè",
    "i": "īíǐì",
    "o": "ōóǒò",
    "u": "ūúǔù",
    "ü": "ǖǘǚǜ",
}


def _mark_syllable(syllable: str, tone: int) -> str:
    """Place a tone mark on the right vowel of one pinyin syllable."""
    if not 1 <= tone <= 4:
        return syllable

    def marked(char: str) -> str:
        return _TONE_MARKS[char][tone - 1]

    # rule 1: 'a' always takes the mark
    index = syllable.find("a")
    if index != -1:
        return syllable[:index] + marked("a") + syllable[index + 1 :]
    # rule 2: otherwise the first 'o' or 'e'
    for char in ("o", "e"):
        index = syllable.find(char)
        if index != -1:
            return syllable[:index] + marked(char) + syllable[index + 1 :]
    # rule 3: otherwise the last vowel ('iu' → u, 'ui' → i)
    for index in range(len(syllable) - 1, -1, -1):
        if syllable[index] in ("i", "u", "ü"):
            char = syllable[index]
            return syllable[:index] + marked(char) + syllable[index + 1 :]
    return syllable


def pinyin_tone_marks(pinyin_field: str) -> str | None:
    """Convert CC-CEDICT pinyin ("chu2 fang2", "Bei3 jing1", "nu:3") to the
    app's tone-mark style ("chú fáng", "Běi jīng", "nǚ").

    Tone 5 (neutral) gets no mark; `u:` becomes ü; separators such as the
    name middle dot pass through unchanged. Returns None for empty input.
    """
    if not pinyin_field or not pinyin_field.strip():
        return None
    pieces: list[str] = []
    for part in pinyin_field.split():
        if part in ("·", ",", "，"):
            pieces.append(part)
            continue
        match = re.match(r"^(.*?)([1-5])$", part)
        if match is None:  # no tone digit — keep as-is
            pieces.append(part.replace("u:", "ü").replace("v:", "ü"))
            continue
        syllable = match.group(1).replace("u:", "ü").replace("v:", "ü")
        tone = int(match.group(2))
        pieces.append(_mark_syllable(syllable, tone))
    return " ".join(pieces)


@dataclass(frozen=True)
class DictEntry:
    """One dictionary entry, ready to store in the words table."""

    headword: str           # simplified headword (matches words.text)
    pinyin: str | None      # tone-mark pinyin, e.g. "chú fáng"
    definition: str         # English, senses joined and capped


def _clean_senses(glosses_field: str) -> list[str]:
    """Split a /gloss/…/ field into senses; drop classifier references."""
    senses = []
    for sense in glosses_field.split("/"):
        sense = sense.strip()
        if not sense or sense.startswith("CL:"):
            continue
        sense = re.sub(r",\s*CL:.*$", "", sense)  # trailing classifier list
        sense = sense.strip()
        if sense:
            senses.append(sense)
    return senses


def _compose_definition(senses: list[str]) -> str | None:
    """Join the first MAX_SENSES senses and cap the total length."""
    senses = senses[:MAX_SENSES]
    if not senses:
        return None
    definition = "; ".join(senses)
    if len(definition) > MAX_DEFINITION_CHARS:
        definition = definition[: MAX_DEFINITION_CHARS - 1].rstrip() + "…"
    return definition

class DictionaryService:
    """Read-only lookup over a CC-CEDICT file (plain text or gzipped)."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._entries: dict[str, DictEntry] = {}
        try:
            self._load()
        except Exception as exc:  # noqa: BLE001 - disable, don't crash the app
            logger.warning("dictionary %s unavailable: %s", self.path, exc)
            self._entries = {}

    @property
    def available(self) -> bool:
        return bool(self._entries)

    def lookup(self, word: str) -> DictEntry | None:
        """Exact match on the simplified headword; None on any miss."""
        if not word:
            return None
        return self._entries.get(word.strip())

    # ---- parsing ----

    def _open(self):
        if self.path.suffix == ".gz":
            return gzip.open(self.path, "rt", encoding="utf-8", errors="strict")
        return self.path.open(encoding="utf-8", errors="strict")

    def _load(self) -> None:
        """Parse the file; homograph lines are grouped per simplified key."""
        entries: dict[str, list[tuple[str | None, list[str]]]] = {}
        with self._open() as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                match = _ENTRY_RE.match(line)
                if match is None:
                    continue
                _traditional, simplified, pinyin_field, glosses = match.groups()
                pinyin = pinyin_tone_marks(pinyin_field)
                senses = _clean_senses(glosses)
                if not senses:
                    continue
                entries.setdefault(simplified, []).append((pinyin, senses))
        for simplified, parsed in entries.items():
            self._entries[simplified] = self._compose_entry(simplified, parsed)

    @staticmethod
    def _compose_entry(headword: str,
                       parsed: list[tuple[str | None, list[str]]]) -> DictEntry:
        """Merge homograph entries: prefer the common-word sense.

        Selection order: non-"variant of" and non-proper-noun entry first
        (CC-CEDICT sometimes lists a name/place sense before the everyday
        one, e.g. 狮子 [Shi1 zi5] "Leo" before [shi1 zi5] "lion"); proper
        nouns are only used when they are all the dictionary has (北京).
        """
        non_variant = [
            candidate for candidate in parsed
            if candidate[1] and not _VARIANT_RE.match(candidate[1][0])
        ] or parsed
        common = [
            candidate for candidate in non_variant
            if not (candidate[0] or "")[:1].isupper()
        ]
        chosen = (common or non_variant)[0]
        pinyin, senses = chosen
        definition = _compose_definition(senses)
        if definition is None:
            # only classifier references; fall back to another entry
            for candidate_pinyin, candidate_senses in parsed:
                definition = _compose_definition(candidate_senses)
                if definition is not None:
                    pinyin = pinyin or candidate_pinyin
                    break
        return DictEntry(headword=headword, pinyin=pinyin,
                         definition=definition or "")


# ---- module-level loader (cached per resolved path) ----

_services: dict[Path, DictionaryService] = {}


def dictionary_resource_available() -> bool:
    """Cheap existence check (no parsing) for the bundled dictionary."""
    return CEDICT_GZ.is_file()


def get_dictionary() -> DictionaryService | None:
    """The configured CC-CEDICT service, or None when disabled/unavailable.

    `LANGREAD_CEDICT` points at a dictionary file (plain or .gz) or is
    "off" to disable lookups; by default the bundled resource is used.
    Parsed services are cached per path — the parse itself runs once.
    """
    override = os.environ.get(ENV_CEDICT, "").strip()
    if override.lower() in ("off", "none", "false", "0"):
        return None
    path = Path(override) if override else CEDICT_GZ
    if path in _services:
        return _services[path]
    service = DictionaryService(path)
    if not service.available:
        return None  # don't cache failures (env overrides may fix the path)
    _services[path] = service
    return service
