# operations-dashboard-demo

![PowerBI](https://img.shields.io/badge/Power%20BI-Reporting-yellow)
![Template](https://img.shields.io/badge/Template-Power%20BI-blue)
![License](https://img.shields.io/badge/License-MIT-brightgreen)

Power BI placeholder workflow with sample operational reporting data.

## Overview

This repository combines sample data, placeholder Power BI artifacts, and reproducible preparation scripts. The generated `.pbix` files are transparent placeholders and should be replaced with real report files once the dashboard is built in Power BI Desktop.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/prepare_dataset.py
```

## Power BI Workflow

1. Open `data/sample_sales.csv` in Power BI Desktop.
2. Build the report pages described in `powerbi/report.metadata.json`.
3. Save the real `.pbix` file back into `powerbi/`.

## Automation Disclosure

**Note:** This repository uses automation and AI assistance for planning, initial scaffolding, routine maintenance, and selected code or documentation generation. I review and curate the outputs as part of my portfolio workflow.

## Added Starter Assets

This starter now includes:

- `scripts/generate_operations_data.py` - generates a sample operational KPI dataset for Power BI
- `data/sample_metrics.csv` - ready-to-load sample operations data referenced by the Power BI metadata
- `docs/dashboard-design.md` - lightweight guidance for shaping the Power BI model, visuals, and KPIs

## Suggested Usage

Generate or refresh the sample dataset:

```bash
python scripts/generate_operations_data.py
```

Then in Power BI Desktop:

1. Load `data/sample_metrics.csv`
2. Parse `date` as a date field
3. Use `site`, `team`, and `shift` as dimensions
4. Build KPI cards for throughput, downtime, quality, and on-time completion
5. Use `docs/dashboard-design.md` as a page and metric guide

## Note

The existing template references both `sample_sales.csv` and `sample_metrics.csv` in different places. The added assets follow the Power BI metadata file and provide `sample_metrics.csv` as the primary reporting dataset.
