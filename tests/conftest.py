"""Shared test configuration.

The bundled CC-CEDICT dictionary is disabled for every test by default so
existing fixtures stay deterministic; dictionary-specific tests point
LANGREAD_CEDICT at a small fixture file (or the real resource).
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _dictionary_off(monkeypatch):
    monkeypatch.setenv("LANGREAD_CEDICT", "off")
