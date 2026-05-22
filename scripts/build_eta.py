#!/usr/bin/env python3
"""Build eta.json from the procurement ETA spreadsheet CSV.

Reads a CSV export of the sheet and emits a compact JSON mapping
UUID -> sorted list of expected receipt dates (ISO YYYY-MM-DD).
The source column "Upcoming Expectedreceiptdates" contains values
formatted like "[2026-05-27]" or "[2026-06-03,2026-05-26]".
"""

from __future__ import annotations

import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

UUID_COL = "Item Extid"
ETA_COL = "Upcoming Expectedreceiptdates"
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def parse_dates(raw: str) -> list[str]:
    return sorted(set(DATE_RE.findall(raw)))


def main(in_path: str, out_path: str) -> int:
    src = Path(in_path)
    if not src.is_file():
        print(f"Input not found: {src}", file=sys.stderr)
        return 1

    mapping: dict[str, list[str]] = {}
    with src.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if UUID_COL not in reader.fieldnames or ETA_COL not in reader.fieldnames:
            print(
                f"Required columns missing. Have: {reader.fieldnames}",
                file=sys.stderr,
            )
            return 2
        for row in reader:
            uuid = (row.get(UUID_COL) or "").strip()
            raw = (row.get(ETA_COL) or "").strip()
            if not uuid or not raw:
                continue
            dates = parse_dates(raw)
            if dates:
                mapping[uuid] = dates

    payload = {
        "fetchedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "https://docs.google.com/spreadsheets/d/1FGsAgYm72Sttg9zK-eGMqnbbIB4d71rDyrpUupAV4OE/edit?gid=0#gid=0",
        "count": len(mapping),
        "eta": mapping,
    }
    Path(out_path).write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {out_path} with {len(mapping)} entries")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: build_eta.py <input.csv> <output.json>", file=sys.stderr)
        sys.exit(64)
    sys.exit(main(sys.argv[1], sys.argv[2]))
