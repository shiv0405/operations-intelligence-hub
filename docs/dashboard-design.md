# Operations Dashboard Design Notes

This repository contains placeholder Power BI metadata plus a sample CSV for a basic operations reporting workflow.

## Dataset Shape

Primary file: `data/sample_metrics.csv`

Recommended field roles:

- Dimensions
  - `date`
  - `site`
  - `team`
  - `shift`
- Base measures
  - `planned_units`
  - `actual_units`
  - `downtime_minutes`
  - `defects`
  - `incidents`
  - `on_time_jobs`
  - `total_jobs`
- Precomputed ratios
  - `quality_rate`
  - `on_time_rate`

## Suggested DAX Measures

Use measures instead of relying only on row-level ratio columns.

```DAX
Total Planned Units = SUM(sample_metrics[planned_units])
Total Actual Units = SUM(sample_metrics[actual_units])
Total Downtime Minutes = SUM(sample_metrics[downtime_minutes])
Total Defects = SUM(sample_metrics[defects])
Total Incidents = SUM(sample_metrics[incidents])

Attainment % = DIVIDE([Total Actual Units], [Total Planned Units], 0)
Quality % = DIVIDE([Total Actual Units] - [Total Defects], [Total Actual Units], 0)
On-Time % = DIVIDE(SUM(sample_metrics[on_time_jobs]), SUM(sample_metrics[total_jobs]), 0)
Units Lost to Downtime = [Total Downtime Minutes] * 0.5
```

Adjust `Units Lost to Downtime` to match a real business assumption.

## Recommended Report Pages

### 1. Executive Summary

Use for quick status checks:

- KPI cards: Actual Units, Attainment %, Quality %, On-Time %, Incidents
- Line chart: Actual vs Planned Units by date
- Clustered bar chart: Actual Units by site
- Slicer row: date, site, shift

### 2. Trend Breakdown

Use for operational patterns over time:

- Line chart: Downtime Minutes by date
- Line chart: Quality % by date
- Stacked column chart: Actual Units by team and shift
- Heatmap or matrix: site x shift with Attainment %

### 3. Operational Detail

Use for drill-down and review:

- Table: date, site, team, shift, planned_units, actual_units, downtime_minutes, defects, incidents
- Conditional formatting on downtime, defects, and incident counts
- Optional drill-through page for a single site

## Modeling Notes

- Mark `date` as a date field in Power BI.
- If the model grows, create a dedicated calendar table and relate it to `sample_metrics[date]`.
- Keep numeric columns as whole numbers except percentages.
- Format `Attainment %`, `Quality %`, and `On-Time %` as percentages.

## Starter Visual Questions

This dataset is useful for answering questions such as:

- Which site is missing plan most often?
- Does the night shift have more downtime?
- Are defects concentrated in a specific team?
- Is on-time execution improving over time?
