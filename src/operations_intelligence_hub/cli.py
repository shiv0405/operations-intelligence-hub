from __future__ import annotations

import argparse
from pathlib import Path

from .config import ProjectPaths
from .data_generation import generate_sample_inputs, write_inputs
from .reporting import run_reporting_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Operations Intelligence Hub CLI")
    parser.add_argument("--project-root", default=".", help="Project root containing data/, artifacts/, and powerbi/")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate_parser = subparsers.add_parser("generate-data", help="Generate synthetic network telemetry datasets")
    generate_parser.add_argument("--days", type=int, default=365)
    generate_parser.add_argument("--sites", type=int, default=12)
    generate_parser.add_argument("--orders-per-site-day", type=int, default=28)
    generate_parser.add_argument("--seed", type=int, default=42)

    subparsers.add_parser("build-report", help="Build scorecards, executive outputs, and Power BI assets from existing data")

    run_all_parser = subparsers.add_parser("run-all", help="Generate datasets and reporting outputs in one pass")
    run_all_parser.add_argument("--days", type=int, default=365)
    run_all_parser.add_argument("--sites", type=int, default=12)
    run_all_parser.add_argument("--orders-per-site-day", type=int, default=28)
    run_all_parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = ProjectPaths.from_root(Path(args.project_root).resolve())
    paths.ensure_directories()

    if args.command in {"generate-data", "run-all"}:
        site_dimension, operations, orders, incidents = generate_sample_inputs(
            days=args.days,
            site_count=args.sites,
            orders_per_site_day=args.orders_per_site_day,
            seed=args.seed,
        )
        write_inputs(
            site_dimension=site_dimension,
            operations=operations,
            orders=orders,
            incidents=incidents,
            site_dimension_path=paths.site_dimension_path,
            operations_path=paths.operations_path,
            orders_path=paths.orders_path,
            incidents_path=paths.incidents_path,
        )
        print(f"Wrote raw datasets to {paths.raw_dir}")

    if args.command in {"build-report", "run-all"}:
        result = run_reporting_pipeline(paths)
        print(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
