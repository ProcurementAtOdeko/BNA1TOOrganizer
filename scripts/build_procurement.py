#!/usr/bin/env python3
"""Build procurement.json from the procurement spreadsheet CSV export.

Captures per-UUID metadata used by the BNA1 dashboard:
  - eta:          column G, parsed list of YYYY-MM-DD strings
  - ohUnits:      column J, on-hand quantity in purchase units
  - consumption:  column K, purchase-unit consumption per day
  - toAvailable:  column L, available TO quantity (purchase units)
  - leadDays:     column M, vendor lead time in days
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
OH_COL = "OH Purchase Unit"
CONS_COL = "Purchase Unit Cons"
TO_AVAIL_COL = "TO QTY Aval"
LEAD_COL = "Lead"

DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def parse_dates(raw: str) -> list[str]:
    return sorted(set(DATE_RE.findall(raw)))


def parse_num(raw):
    if raw is None:
        return None
    s = raw.strip().replace(",", "")
    if not s:
        return None
    try:
        n = float(s)
    except ValueError:
        return None
    return int(n) if n.is_integer() else round(n, 4)


def main(in_path: str, out_path: str) -> int:
    src = Path(in_path)
    if not src.is_file():
        print(f"Input not found: {src}", file=sys.stderr)
        return 1

    items: dict = {}
    with src.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = [UUID_COL, ETA_COL, OH_COL, CONS_COL, TO_AVAIL_COL, LEAD_COL]
        missing = [c for c in required if c not in (reader.fieldnames or [])]
        if missing:
            print(
                f"Required columns missing: {missing}. Have: {reader.fieldnames}",
                file=sys.stderr,
            )
            return 2

        for row in reader:
            uuid = (row.get(UUID_COL) or "").strip()
            if not uuid:
                continue

            record = {}
            dates = parse_dates(row.get(ETA_COL) or "")
            if dates:
                record["eta"] = dates

            for key, col in (
                ("ohUnits", OH_COL),
                ("consumption", CONS_COL),
                ("toAvailable", TO_AVAIL_COL),
                ("leadDays", LEAD_COL),
            ):
                v = parse_num(row.get(col))
                if v is not None:
                    record[key] = v

            if record:
                items[uuid] = record

    payload = {
        "fetchedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "https://docs.google.com/spreadsheets/d/1FGsAgYm72Sttg9zK-eGMqnbbIB4d71rDyrpUupAV4OE/edit?gid=0#gid=0",
        "count": len(items),
        "items": items,
    }
    Path(out_path).write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {out_path} with {len(items)} entries")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: build_procurement.py <input.csv> <output.json>", file=sys.stderr)
        sys.exit(64)
    sys.exit(main(sys.argv[1], sys.argv[2]))
