from __future__ import annotations

from pathlib import Path

from operations_intelligence_hub.config import ProjectPaths
from operations_intelligence_hub.data_generation import generate_sample_inputs, write_inputs
from operations_intelligence_hub.reporting import run_reporting_pipeline


def test_operations_intelligence_pipeline_generates_outputs(tmp_path: Path) -> None:
    paths = ProjectPaths.from_root(tmp_path)
    paths.ensure_directories()

    site_dimension, operations, orders, incidents = generate_sample_inputs(
        days=40,
        site_count=5,
        orders_per_site_day=12,
        seed=7,
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

    result = run_reporting_pipeline(paths)

    assert result["sites"] == 5
    assert result["network_score"] >= 70
    assert Path(result["outputs"]["scorecard_path"]).exists()
    assert Path(result["outputs"]["executive_html_path"]).exists()
    assert Path(result["outputs"]["dashboard_preview_path"]).exists()
