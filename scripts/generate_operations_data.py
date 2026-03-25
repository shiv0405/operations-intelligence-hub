from __future__ import annotations

from pathlib import Path
from datetime import date, timedelta
import csv


OUTPUT = Path(__file__).resolve().parents[1] / "data" / "sample_metrics.csv"

SITES = [
    ("North Hub", "Inbound"),
    ("North Hub", "Outbound"),
    ("South Hub", "Assembly"),
    ("South Hub", "Packaging"),
]
SHIFTS = ["Day", "Night"]


def daterange(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def build_row(current_date: date, site: str, team: str, shift: str) -> list[str]:
    day_index = current_date.toordinal()
    site_factor = sum(ord(ch) for ch in site) % 17
    team_factor = sum(ord(ch) for ch in team) % 11
    shift_factor = 6 if shift == "Night" else 0

    planned_units = 180 + (day_index % 9) * 6 + site_factor
    actual_units = planned_units - ((day_index + team_factor + shift_factor) % 14) + 4
    downtime_minutes = 18 + ((day_index + site_factor + shift_factor) % 43)
    defects = 2 + ((day_index + team_factor) % 7)
    incidents = (day_index + site_factor + team_factor + shift_factor) % 3
    on_time_jobs = 22 + ((day_index + site_factor) % 8)
    total_jobs = on_time_jobs + 1 + ((day_index + shift_factor) % 4)

    quality_rate = round((actual_units - defects) / actual_units, 4)
    on_time_rate = round(on_time_jobs / total_jobs, 4)

    return [
        current_date.isoformat(),
        site,
        team,
        shift,
        str(planned_units),
        str(actual_units),
        str(downtime_minutes),
        str(defects),
        str(incidents),
        str(on_time_jobs),
        str(total_jobs),
        f"{quality_rate:.4f}",
        f"{on_time_rate:.4f}",
    ]


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    header = [
        "date",
        "site",
        "team",
        "shift",
        "planned_units",
        "actual_units",
        "downtime_minutes",
        "defects",
        "incidents",
        "on_time_jobs",
        "total_jobs",
        "quality_rate",
        "on_time_rate",
    ]

    rows = [header]
    for current_date in daterange(date(2026, 1, 1), date(2026, 2, 28)):
        for site, team in SITES:
            for shift in SHIFTS:
                rows.append(build_row(current_date, site, team, shift))

    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerows(rows)

    print(f"Wrote {len(rows) - 1} records to {OUTPUT}")


if __name__ == "__main__":
    main()
