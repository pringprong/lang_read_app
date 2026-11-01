"""Build the bundled HSK 1–6 CSV from the complete-hsk-vocabulary dataset.

Source: https://github.com/drkameleon/complete-hsk-vocabulary (MIT license)
Downloaded via jsDelivr CDN (see docs/smoke_checklist.md) into /tmp/hsk/{1..6}.json
using the *exclusive* old-standard wordlists (words introduced at each level).

Output: src/langread/resources/hsk/hsk.csv with columns: level,text,pinyin,definition
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

SOURCE_DIR = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/hsk")
OUTPUT = Path(__file__).parents[1] / "src" / "langread" / "resources" / "hsk" / "hsk.csv"

MAX_DEFINITION_LEN = 200


def definition_of(entry: dict) -> str:
    forms = entry.get("f") or []
    if not forms:
        return ""
    meanings = forms[0].get("m") or []
    joined = "; ".join(meanings)
    return joined[:MAX_DEFINITION_LEN]


def pinyin_of(entry: dict) -> str:
    forms = entry.get("f") or []
    if not forms:
        return ""
    return (forms[0].get("i") or {}).get("y", "")


def main() -> None:
    rows: list[tuple[int, str, str, str]] = []
    seen: set[str] = set()
    for level in range(1, 7):
        path = SOURCE_DIR / f"{level}.json"
        entries = json.loads(path.read_text(encoding="utf-8"))
        added = 0
        for entry in sorted(entries, key=lambda e: e["s"]):
            text = entry["s"].strip()
            if not text or text in seen:
                continue  # keep only the first (lowest) level per word
            seen.add(text)
            rows.append((level, text, pinyin_of(entry), definition_of(entry)))
            added += 1
        print(f"level {level}: {len(entries)} entries, {added} unique new words")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["level", "text", "pinyin", "definition"])
        writer.writerows(rows)
    print(f"wrote {len(rows)} words to {OUTPUT}")


if __name__ == "__main__":
    main()
