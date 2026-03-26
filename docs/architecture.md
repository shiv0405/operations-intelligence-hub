# Architecture Overview

Operations Intelligence Hub is structured to feel like a reporting accelerator that could sit between operational source systems and a BI delivery layer.

## Layers

1. `data_generation.py`
   Generates reproducible synthetic source data for sites, shift-level operations, order service execution, and operational incidents.
2. `reporting.py`
   Curates the source data into scorecards, alerts, KPI snapshots, and executive reporting outputs.
3. `powerbi/`
   Contains the semantic model, reusable DAX, theming, and dashboard blueprint used to turn the curated data into a polished command center.

## Data Flow

- Raw synthetic telemetry lands in `data/raw/`
- Curated scorecards and alerts land in `data/processed/`
- Executive-facing artifacts land in `artifacts/`
- Report-modeling assets land in `powerbi/`

## Production Extension Path

- Swap the synthetic generators for warehouse or lakehouse extracts
- Add orchestration for scheduled refresh and validation
- Publish curated outputs into a governed semantic layer
- Expose selected KPIs through APIs or internal portals for operational review
