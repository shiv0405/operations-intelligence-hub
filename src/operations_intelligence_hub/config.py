from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    raw_dir: Path
    processed_dir: Path
    artifacts_dir: Path
    powerbi_dir: Path
    docs_dir: Path
    site_dimension_path: Path
    operations_path: Path
    orders_path: Path
    incidents_path: Path
    scorecard_path: Path
    alerts_path: Path
    executive_snapshot_path: Path
    root_cause_path: Path
    executive_brief_path: Path
    executive_html_path: Path
    measures_path: Path
    semantic_model_path: Path
    dashboard_blueprint_path: Path
    dashboard_preview_path: Path
    theme_path: Path

    @classmethod
    def from_root(cls, root: Path | None = None) -> "ProjectPaths":
        resolved_root = (root or Path(__file__).resolve().parents[2]).resolve()
        raw_dir = resolved_root / "data" / "raw"
        processed_dir = resolved_root / "data" / "processed"
        artifacts_dir = resolved_root / "artifacts"
        powerbi_dir = resolved_root / "powerbi"
        docs_dir = resolved_root / "docs"
        return cls(
            root=resolved_root,
            raw_dir=raw_dir,
            processed_dir=processed_dir,
            artifacts_dir=artifacts_dir,
            powerbi_dir=powerbi_dir,
            docs_dir=docs_dir,
            site_dimension_path=raw_dir / "site_dimension.csv",
            operations_path=raw_dir / "operations_performance_daily.csv",
            orders_path=raw_dir / "order_service_levels.csv",
            incidents_path=raw_dir / "quality_incidents.csv",
            scorecard_path=processed_dir / "site_performance_scorecard.csv",
            alerts_path=processed_dir / "network_alerts.csv",
            executive_snapshot_path=artifacts_dir / "executive_kpi_snapshot.json",
            root_cause_path=artifacts_dir / "root_cause_summary.csv",
            executive_brief_path=artifacts_dir / "executive_brief.md",
            executive_html_path=artifacts_dir / "executive_summary.html",
            measures_path=powerbi_dir / "measures.dax",
            semantic_model_path=powerbi_dir / "semantic_model.json",
            dashboard_blueprint_path=powerbi_dir / "dashboard_blueprint.md",
            dashboard_preview_path=powerbi_dir / "dashboard_preview.html",
            theme_path=powerbi_dir / "theme.json",
        )

    def ensure_directories(self) -> None:
        for directory in (
            self.raw_dir,
            self.processed_dir,
            self.artifacts_dir,
            self.powerbi_dir,
            self.docs_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)
