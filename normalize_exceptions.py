import csv
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone

TERMINAL_MAP = {
    "terminal 3": "Terminal 3",
    "t3": "Terminal 3",
}

def normalize_timestamp(value):
    value = (value or "").strip()
    formats = [
        ("%Y-%m-%d %H:%M:%S", False),
        ("%m/%d/%Y %H:%M", False),
        ("%Y-%m-%dT%H:%M:%SZ", True),
    ]

    for fmt, is_utc in formats:
        try:
            result = datetime.strptime(value, fmt)
            if is_utc:
                return result.replace(
                    tzinfo=timezone.utc
                ).isoformat().replace("+00:00", "Z"), None
            return result.strftime("%Y-%m-%d %H:%M:%S"), None
        except ValueError:
            pass

    return None, f"Unrecognized timestamp: {value!r}"

def normalize_terminal(value):
    value = re.sub(r"\s+", " ", (value or "").strip())
    if not value:
        return None, "Terminal is blank"
    return TERMINAL_MAP.get(value.casefold(), value), None

def normalize_carrier(value):
    value = (value or "").strip()
    if not value:
        return None, "Carrier code is missing; identity not inferred"
    if re.fullmatch(r"[A-Za-z0-9_-]+", value):
        return value.upper(), None
    return value, f"Unusual carrier code retained: {value!r}"

def main():
    source = sys.argv[1] if len(sys.argv) > 1 else "exception_export.csv"
    records = []
    warnings = []
    counts = Counter()

    with open(source, newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        required = {
            "exception_id", "terminal", "event_type",
            "carrier_code", "event_ts"
        }
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("CSV is missing required columns")

        for line, row in enumerate(reader, start=2):
            terminal, tw = normalize_terminal(row["terminal"])
            carrier, cw = normalize_carrier(row["carrier_code"])
            timestamp, dw = normalize_timestamp(row["event_ts"])
            event = (row["event_type"] or "").strip().lower()
            event = re.sub(r"\s+", "_", event) or None

            record = {
                "exception_id": row["exception_id"].strip(),
                "terminal": terminal,
                "event_type": event,
                "carrier_code": carrier,
                "event_ts": timestamp,
            }
            records.append(record)

            if event:
                counts[event] += 1
            else:
                warnings.append(
                    f"Line {line}: event type is blank; not counted"
                )

            for field, warning in [
                ("terminal", tw),
                ("carrier_code", cw),
                ("event_ts", dw),
            ]:
                if warning:
                    warnings.append(
                        f"Line {line}, {record['exception_id']}, "
                        f"{field}: {warning}"
                    )

    result = {
        "records_processed": len(records),
        "event_type_counts": dict(sorted(counts.items())),
        "normalized_records": records,
        "warnings": warnings,
        "limitations": [
            "Timezone is not inferred for timestamps without a timezone.",
            "Missing carrier identities are not guessed.",
        ],
    }
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()