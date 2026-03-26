# Dashboard Build Guide

Use the curated outputs in this repository to assemble a strong Power BI command center.

## Recommended Import Order

1. `data/raw/site_dimension.csv`
2. `data/raw/operations_performance_daily.csv`
3. `data/raw/order_service_levels.csv`
4. `data/raw/quality_incidents.csv`
5. `data/processed/site_performance_scorecard.csv`
6. `data/processed/network_alerts.csv`

## Modeling Guidance

- Use `site_code` as the primary relationship key across all tables
- Add a dedicated calendar table connected to `date` and `order_date`
- Keep scorecards and alerts as curated supporting tables rather than replacing the granular fact tables
- Use `powerbi/measures.dax` as the baseline KPI layer and extend it only where the narrative needs more depth

## Page Flow

- Start with the command center page for executive review
- Follow with site deep dives and delay-driver analysis
- Close with capacity planning and recovery actions
