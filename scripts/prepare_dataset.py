from __future__ import annotations

from pathlib import Path
import csv


DESTINATION = Path(__file__).resolve().parents[1] / "data" / "sample_sales.csv"


def main() -> None:
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        ["month", "region", "sales", "target"],
        ["2026-01", "EMEA", "120000", "110000"],
        ["2026-02", "EMEA", "128500", "115000"],
        ["2026-03", "EMEA", "135200", "120000"],
    ]
    with DESTINATION.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerows(rows)


if __name__ == "__main__":
    main()

