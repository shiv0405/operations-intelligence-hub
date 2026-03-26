from __future__ import annotations

import json
from textwrap import dedent

import pandas as pd

from .config import ProjectPaths


def _safe_divide(numerator: pd.Series | float, denominator: pd.Series | float) -> pd.Series | float:
    if isinstance(denominator, pd.Series):
        denominator = denominator.replace(0, pd.NA)
        result = numerator / denominator
        return result.fillna(0)
    return 0 if denominator == 0 else numerator / denominator


def _scaled(series: pd.Series) -> pd.Series:
    spread = series.max() - series.min()
    if spread <= 0:
        return pd.Series([1.0] * len(series), index=series.index)
    return (series - series.min()) / spread


def build_site_scorecard(
    *,
    site_dimension: pd.DataFrame,
    operations: pd.DataFrame,
    orders: pd.DataFrame,
    incidents: pd.DataFrame,
) -> pd.DataFrame:
    operations_site = (
        operations.groupby(["site_code", "site_name", "region", "country"], as_index=False)
        .agg(
            planned_units=("planned_units", "sum"),
            actual_units=("actual_units", "sum"),
            available_minutes=("available_minutes", "sum"),
            downtime_minutes=("downtime_minutes", "sum"),
            scrap_units=("scrap_units", "sum"),
            backlog_orders=("backlog_orders", "mean"),
            labor_hours=("labor_hours", "sum"),
            overtime_hours=("overtime_hours", "sum"),
            energy_cost_usd=("energy_cost_usd", "sum"),
            safety_near_misses=("safety_near_misses", "sum"),
        )
    )

    orders_site = (
        orders.groupby(["site_code", "site_name", "region", "country"], as_index=False)
        .agg(
            total_orders=("order_id", "count"),
            shipped_on_time=("shipped_on_time", "sum"),
            perfect_orders=("perfect_order_flag", "sum"),
            delayed_orders=("delay_hours", lambda values: int((values > 0).sum())),
            average_cycle_hours=("actual_cycle_hours", "mean"),
            expedites=("expedite_flag", "sum"),
            order_value_usd=("order_value_usd", "sum"),
        )
    )

    incidents_with_weight = incidents.assign(
        severity_weight=incidents["severity"].map({"low": 1, "medium": 2, "high": 3, "critical": 4}).fillna(1)
    )
    incidents_site = (
        incidents_with_weight.groupby(["site_code", "site_name", "region"], as_index=False)
        .agg(
            total_incidents=("incident_id", "count"),
            critical_incidents=("severity", lambda values: int(values.isin(["critical", "high"]).sum())),
            average_resolution_hours=("resolution_hours", "mean"),
            weighted_severity=("severity_weight", "sum"),
        )
    )

    scorecard = (
        site_dimension.merge(operations_site, on=["site_code", "site_name", "region", "country"], how="left")
        .merge(orders_site, on=["site_code", "site_name", "region", "country"], how="left")
        .merge(incidents_site, on=["site_code", "site_name", "region"], how="left")
        .fillna(
            {
                "planned_units": 0,
                "actual_units": 0,
                "available_minutes": 0,
                "downtime_minutes": 0,
                "scrap_units": 0,
                "backlog_orders": 0,
                "labor_hours": 0,
                "overtime_hours": 0,
                "energy_cost_usd": 0.0,
                "safety_near_misses": 0,
                "total_orders": 0,
                "shipped_on_time": 0,
                "perfect_orders": 0,
                "delayed_orders": 0,
                "average_cycle_hours": 0.0,
                "expedites": 0,
                "order_value_usd": 0.0,
                "total_incidents": 0,
                "critical_incidents": 0,
                "average_resolution_hours": 0.0,
                "weighted_severity": 0,
            }
        )
    )

    scorecard["throughput_attainment"] = _safe_divide(scorecard["actual_units"], scorecard["planned_units"])
    scorecard["availability_rate"] = 1 - _safe_divide(scorecard["downtime_minutes"], scorecard["available_minutes"])
    scorecard["first_pass_yield"] = 1 - _safe_divide(scorecard["scrap_units"], scorecard["actual_units"])
    scorecard["on_time_rate"] = _safe_divide(scorecard["shipped_on_time"], scorecard["total_orders"])
    scorecard["perfect_order_rate"] = _safe_divide(scorecard["perfect_orders"], scorecard["total_orders"])
    scorecard["productivity_units_per_hour"] = _safe_divide(scorecard["actual_units"], scorecard["labor_hours"])
    scorecard["incident_rate_per_1000_orders"] = _safe_divide(scorecard["total_incidents"] * 1000, scorecard["total_orders"])
    scorecard["backlog_pressure"] = _safe_divide(scorecard["backlog_orders"], scorecard["daily_capacity"])
    scorecard["oee_proxy"] = (
        scorecard["availability_rate"] * scorecard["throughput_attainment"] * scorecard["first_pass_yield"]
    )

    productivity_scaled = _scaled(scorecard["productivity_units_per_hour"])
    incident_scaled = _scaled(scorecard["incident_rate_per_1000_orders"])
    backlog_scaled = _scaled(scorecard["backlog_pressure"])

    scorecard["composite_score"] = (
        scorecard["availability_rate"] * 18
        + scorecard["throughput_attainment"] * 18
        + scorecard["first_pass_yield"] * 18
        + scorecard["on_time_rate"] * 18
        + scorecard["perfect_order_rate"] * 12
        + productivity_scaled * 9
        + (1 - incident_scaled) * 4
        + (1 - backlog_scaled) * 3
    ).round(3)
    scorecard["composite_score"] = (scorecard["composite_score"] * 100 / 100).round(1)

    scorecard["performance_band"] = "Stable"
    scorecard.loc[scorecard["composite_score"] >= 86, "performance_band"] = "Leading"
    scorecard.loc[scorecard["composite_score"] < 78, "performance_band"] = "Watchlist"
    scorecard.loc[scorecard["composite_score"] < 70, "performance_band"] = "Critical"

    scorecard["executive_priority"] = "Maintain cadence"
    scorecard.loc[
        (scorecard["performance_band"] == "Watchlist")
        | (scorecard["backlog_pressure"] > 0.14)
        | (scorecard["critical_incidents"] >= 10),
        "executive_priority",
    ] = "Stabilize service flow"
    scorecard.loc[
        (scorecard["performance_band"] == "Critical")
        | (scorecard["critical_incidents"] >= 16)
        | (scorecard["on_time_rate"] < 0.91),
        "executive_priority",
    ] = "Immediate leadership intervention"

    scorecard = scorecard.sort_values(["composite_score", "on_time_rate"], ascending=[False, False]).reset_index(drop=True)
    scorecard["rank"] = scorecard.index + 1
    return scorecard[
        [
            "rank",
            "site_code",
            "site_name",
            "region",
            "country",
            "automation_tier",
            "network_role",
            "throughput_attainment",
            "availability_rate",
            "first_pass_yield",
            "on_time_rate",
            "perfect_order_rate",
            "oee_proxy",
            "backlog_pressure",
            "incident_rate_per_1000_orders",
            "productivity_units_per_hour",
            "energy_cost_usd",
            "order_value_usd",
            "critical_incidents",
            "performance_band",
            "executive_priority",
            "composite_score",
        ]
    ]


def build_network_alerts(scorecard: pd.DataFrame) -> pd.DataFrame:
    alerts = scorecard.loc[
        (scorecard["performance_band"].isin(["Watchlist", "Critical"]))
        | (scorecard["backlog_pressure"] > 0.12)
        | (scorecard["critical_incidents"] >= 12)
    ].copy()
    alerts["risk_signal"] = "Backlog and service pressure"
    alerts.loc[alerts["critical_incidents"] >= 12, "risk_signal"] = "Operational incident concentration"
    alerts.loc[alerts["performance_band"] == "Critical", "risk_signal"] = "Executive escalation required"
    alerts["recommended_action"] = "Launch site-level recovery sprint"
    alerts.loc[alerts["critical_incidents"] >= 12, "recommended_action"] = "Assign cross-functional incident review"
    alerts.loc[alerts["backlog_pressure"] > 0.15, "recommended_action"] = "Rebalance capacity and carrier allocation"
    alerts = alerts.sort_values(["performance_band", "composite_score", "backlog_pressure"], ascending=[True, True, False])
    return alerts[
        [
            "site_code",
            "site_name",
            "region",
            "performance_band",
            "composite_score",
            "backlog_pressure",
            "critical_incidents",
            "risk_signal",
            "recommended_action",
        ]
    ].reset_index(drop=True)


def build_root_cause_summary(orders: pd.DataFrame, incidents: pd.DataFrame) -> pd.DataFrame:
    delayed_orders = orders.loc[orders["root_cause"] != "On-plan"]
    order_summary = (
        delayed_orders.groupby("root_cause", as_index=False)
        .agg(
            delayed_orders=("order_id", "count"),
            value_at_risk_usd=("order_value_usd", "sum"),
        )
        .rename(columns={"root_cause": "driver"})
    )
    incident_summary = (
        incidents.groupby("category", as_index=False)
        .agg(
            incident_count=("incident_id", "count"),
            impacted_orders=("impacted_orders", "sum"),
        )
        .rename(columns={"category": "driver"})
    )
    summary = order_summary.merge(incident_summary, on="driver", how="outer").fillna(0)
    summary["weighted_impact"] = (
        summary["delayed_orders"] * 2.5 + summary["incident_count"] * 3.0 + summary["value_at_risk_usd"] / 25000
    )
    summary = summary.sort_values("weighted_impact", ascending=False).reset_index(drop=True)
    return summary


def build_kpi_snapshot(scorecard: pd.DataFrame, operations: pd.DataFrame, orders: pd.DataFrame, alerts: pd.DataFrame) -> dict[str, object]:
    value_at_risk = orders.loc[orders["shipped_on_time"] == 0, "order_value_usd"].sum()
    return {
        "sites_in_scope": int(scorecard.shape[0]),
        "network_score": round(float(scorecard["composite_score"].mean()), 1),
        "leading_sites": int((scorecard["performance_band"] == "Leading").sum()),
        "critical_sites": int((scorecard["performance_band"] == "Critical").sum()),
        "throughput_attainment_pct": round(float(operations["actual_units"].sum() / operations["planned_units"].sum() * 100), 1),
        "availability_pct": round(float((1 - operations["downtime_minutes"].sum() / operations["available_minutes"].sum()) * 100), 1),
        "first_pass_yield_pct": round(float((1 - operations["scrap_units"].sum() / operations["actual_units"].sum()) * 100), 1),
        "on_time_service_pct": round(float(orders["shipped_on_time"].mean() * 100), 1),
        "perfect_order_pct": round(float(orders["perfect_order_flag"].mean() * 100), 1),
        "revenue_at_risk_usd": round(float(value_at_risk), 2),
        "expedite_share_pct": round(float(orders["expedite_flag"].mean() * 100), 1),
        "top_priority_site": str(alerts.iloc[0]["site_name"]) if not alerts.empty else str(scorecard.sort_values("composite_score").iloc[0]["site_name"]),
    }


def _format_percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def build_executive_brief(snapshot: dict[str, object], scorecard: pd.DataFrame, alerts: pd.DataFrame, root_causes: pd.DataFrame) -> str:
    strongest = scorecard.iloc[0]
    weakest = scorecard.sort_values("composite_score").iloc[0]
    top_driver = root_causes.iloc[0]["driver"] if not root_causes.empty else "No dominant driver identified"
    return dedent(
        f"""\
        # Executive Brief

        Operations Intelligence Hub models a {snapshot["sites_in_scope"]}-site network with a composite network score of {snapshot["network_score"]}.

        ## Leadership Takeaways

        - Throughput attainment is {snapshot["throughput_attainment_pct"]}% with availability at {snapshot["availability_pct"]}%.
        - On-time service is {snapshot["on_time_service_pct"]}% and perfect-order execution is {snapshot["perfect_order_pct"]}%.
        - Revenue at risk from delayed orders is estimated at ${snapshot["revenue_at_risk_usd"]:,.2f}.
        - {alerts.shape[0]} sites are currently flagged for intervention.

        ## Best Performing Site

        - {strongest["site_name"]} leads the network with a composite score of {strongest["composite_score"]}.
        - Its key strengths are availability {_format_percent(strongest["availability_rate"])} and on-time service {_format_percent(strongest["on_time_rate"])}.

        ## Priority Site

        - {weakest["site_name"]} requires attention with a composite score of {weakest["composite_score"]}.
        - Recommended action: {weakest["executive_priority"]}.

        ## Primary Root-Cause Driver

        - The highest-weighted network issue is `{top_driver}` based on delayed-order exposure and incident concentration.
        """
    )


def build_executive_html(snapshot: dict[str, object], scorecard: pd.DataFrame, alerts: pd.DataFrame, root_causes: pd.DataFrame) -> str:
    top_sites = scorecard.head(5)[["site_name", "region", "composite_score", "on_time_rate", "first_pass_yield"]]
    attention_sites = scorecard.sort_values("composite_score").head(5)[["site_name", "region", "composite_score", "backlog_pressure", "executive_priority"]]
    root_rows = root_causes.head(6)[["driver", "delayed_orders", "incident_count", "value_at_risk_usd"]]

    def render_rows(frame: pd.DataFrame, percent_columns: set[str] | None = None, money_columns: set[str] | None = None) -> str:
        percent_columns = percent_columns or set()
        money_columns = money_columns or set()
        rows = []
        for row in frame.itertuples(index=False):
            cells = []
            for column, value in zip(frame.columns, row):
                if column in percent_columns:
                    formatted = f"{float(value) * 100:.1f}%"
                elif column in money_columns:
                    formatted = f"${float(value):,.0f}"
                elif isinstance(value, float):
                    formatted = f"{value:.1f}"
                else:
                    formatted = str(value)
                cells.append(f"<td>{formatted}</td>")
            rows.append("<tr>" + "".join(cells) + "</tr>")
        return "".join(rows)

    metric_cards = [
        ("Network Score", snapshot["network_score"], ""),
        ("On-Time Service", snapshot["on_time_service_pct"], "%"),
        ("Perfect Order", snapshot["perfect_order_pct"], "%"),
        ("Revenue At Risk", snapshot["revenue_at_risk_usd"], "$"),
        ("Critical Sites", snapshot["critical_sites"], ""),
        ("Expedite Share", snapshot["expedite_share_pct"], "%"),
    ]

    card_markup = []
    for label, value, suffix in metric_cards:
        display = f"${value:,.0f}" if suffix == "$" else f"{value}{suffix}"
        card_markup.append(
            f"""
            <div class="card">
              <span class="label">{label}</span>
              <strong>{display}</strong>
            </div>
            """
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Operations Intelligence Hub - Executive Summary</title>
  <style>
    :root {{
      --bg: #f4f1ea;
      --ink: #17202a;
      --card: #fffdf8;
      --accent: #035e7b;
      --accent-soft: #d9eef4;
      --border: #d4cbc0;
      --muted: #576574;
    }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "Trebuchet MS", sans-serif;
      background: linear-gradient(180deg, #f7f4ee 0%, #efe8dc 100%);
      color: var(--ink);
    }}
    .wrap {{
      max-width: 1240px;
      margin: 0 auto;
      padding: 36px 28px 56px;
    }}
    h1 {{
      font-size: 38px;
      margin-bottom: 10px;
    }}
    p.subtitle {{
      max-width: 840px;
      line-height: 1.6;
      color: var(--muted);
      margin-bottom: 24px;
    }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
      margin: 24px 0 30px;
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 18px 20px;
      box-shadow: 0 18px 30px rgba(23, 32, 42, 0.06);
    }}
    .card .label {{
      display: block;
      color: var(--muted);
      font-size: 13px;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      margin-bottom: 10px;
    }}
    .card strong {{
      font-size: 30px;
    }}
    .panel-grid {{
      display: grid;
      grid-template-columns: 1.5fr 1fr;
      gap: 18px;
    }}
    .panel {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 22px 24px;
      margin-top: 18px;
      box-shadow: 0 18px 30px rgba(23, 32, 42, 0.06);
    }}
    .focus {{
      background: linear-gradient(135deg, var(--accent-soft), #f8fffd);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 12px;
      font-size: 14px;
    }}
    th, td {{
      padding: 10px 8px;
      border-bottom: 1px solid #ebe3d8;
      text-align: left;
    }}
    th {{
      font-size: 12px;
      letter-spacing: 0.04em;
      color: var(--muted);
      text-transform: uppercase;
    }}
    .pill {{
      display: inline-block;
      padding: 6px 10px;
      border-radius: 999px;
      background: rgba(3, 94, 123, 0.1);
      color: var(--accent);
      font-size: 12px;
      margin-right: 8px;
      margin-bottom: 8px;
    }}
    ul {{
      line-height: 1.7;
      padding-left: 20px;
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Operations Intelligence Hub</h1>
    <p class="subtitle">Executive-ready view of network throughput, service health, operational stability, and recovery priorities across a multi-region fulfillment portfolio. This summary is generated from reproducible synthetic telemetry and aligned to the Power BI build assets included in the repository.</p>
    <div class="cards">
      {"".join(card_markup)}
    </div>
    <div class="panel-grid">
      <section class="panel focus">
        <h2>Leadership Narrative</h2>
        <span class="pill">Top Priority: {snapshot["top_priority_site"]}</span>
        <span class="pill">Sites in Scope: {snapshot["sites_in_scope"]}</span>
        <span class="pill">Leading Sites: {snapshot["leading_sites"]}</span>
        <ul>
          <li>Throughput attainment is {snapshot["throughput_attainment_pct"]}% with availability at {snapshot["availability_pct"]}%.</li>
          <li>Delayed-order exposure totals ${snapshot["revenue_at_risk_usd"]:,.0f}, concentrated in sites with elevated backlog pressure.</li>
          <li>The current portfolio demands targeted recovery actions rather than broad network-wide intervention.</li>
        </ul>
      </section>
      <section class="panel">
        <h2>Immediate Actions</h2>
        <ul>
          <li>Stabilize the lowest-scoring sites with a 30-day service recovery sprint focused on backlog, staffing, and carrier allocation.</li>
          <li>Use the Power BI command center pages to separate structural service risk from temporary seasonal pressure.</li>
          <li>Prioritize root-cause remediation where delayed-order value and incident concentration overlap.</li>
        </ul>
      </section>
    </div>
    <section class="panel">
      <h2>Top Performing Sites</h2>
      <table>
        <thead><tr>{"".join(f"<th>{column.replace('_', ' ')}</th>" for column in top_sites.columns)}</tr></thead>
        <tbody>{render_rows(top_sites, percent_columns={"on_time_rate", "first_pass_yield"})}</tbody>
      </table>
    </section>
    <section class="panel">
      <h2>Attention Sites</h2>
      <table>
        <thead><tr>{"".join(f"<th>{column.replace('_', ' ')}</th>" for column in attention_sites.columns)}</tr></thead>
        <tbody>{render_rows(attention_sites, percent_columns={"backlog_pressure"})}</tbody>
      </table>
    </section>
    <section class="panel">
      <h2>Root-Cause Concentration</h2>
      <table>
        <thead><tr>{"".join(f"<th>{column.replace('_', ' ')}</th>" for column in root_rows.columns)}</tr></thead>
        <tbody>{render_rows(root_rows, money_columns={"value_at_risk_usd"})}</tbody>
      </table>
    </section>
  </div>
</body>
</html>
"""


def build_measures_dax() -> str:
    return dedent(
        """\
        Total Planned Units = SUM(OperationsPerformanceDaily[planned_units])
        Total Actual Units = SUM(OperationsPerformanceDaily[actual_units])
        Total Downtime Minutes = SUM(OperationsPerformanceDaily[downtime_minutes])
        Total Scrap Units = SUM(OperationsPerformanceDaily[scrap_units])
        Total Labor Hours = SUM(OperationsPerformanceDaily[labor_hours])
        Total Orders = COUNTROWS(OrderServiceLevels)
        Total Revenue = SUM(OrderServiceLevels[order_value_usd])
        Total Delayed Orders = CALCULATE(COUNTROWS(OrderServiceLevels), OrderServiceLevels[shipped_on_time] = 0)
        Total Perfect Orders = CALCULATE(COUNTROWS(OrderServiceLevels), OrderServiceLevels[perfect_order_flag] = 1)
        Throughput Attainment % = DIVIDE([Total Actual Units], [Total Planned Units], 0)
        Availability % = 1 - DIVIDE([Total Downtime Minutes], SUM(OperationsPerformanceDaily[available_minutes]), 0)
        First Pass Yield % = 1 - DIVIDE([Total Scrap Units], [Total Actual Units], 0)
        On-Time Service % = DIVIDE(CALCULATE(COUNTROWS(OrderServiceLevels), OrderServiceLevels[shipped_on_time] = 1), [Total Orders], 0)
        Perfect Order % = DIVIDE([Total Perfect Orders], [Total Orders], 0)
        Productivity Units per Hour = DIVIDE([Total Actual Units], [Total Labor Hours], 0)
        Incident Count = COUNTROWS(QualityIncidents)
        Critical Incident Count = CALCULATE(COUNTROWS(QualityIncidents), QualityIncidents[severity] IN {"high", "critical"})
        Revenue At Risk = CALCULATE(SUM(OrderServiceLevels[order_value_usd]), OrderServiceLevels[shipped_on_time] = 0)
        Expedite Share % = DIVIDE(CALCULATE(COUNTROWS(OrderServiceLevels), OrderServiceLevels[expedite_flag] = 1), [Total Orders], 0)
        Network Score = AVERAGE(SitePerformanceScorecard[composite_score])
        """
    )


def build_semantic_model(scorecard: pd.DataFrame, alerts: pd.DataFrame, snapshot: dict[str, object]) -> dict[str, object]:
    return {
        "project": "Operations Intelligence Hub",
        "summary": snapshot,
        "tables": [
            {
                "name": "SiteDimension",
                "grain": "One row per site",
                "path": "data/raw/site_dimension.csv",
                "columns": [
                    "site_code",
                    "site_name",
                    "region",
                    "country",
                    "automation_tier",
                    "network_role",
                    "daily_capacity",
                ],
            },
            {
                "name": "OperationsPerformanceDaily",
                "grain": "One row per site, shift, workstream, and day",
                "path": "data/raw/operations_performance_daily.csv",
                "columns": [
                    "date",
                    "site_code",
                    "shift",
                    "workstream",
                    "planned_units",
                    "actual_units",
                    "downtime_minutes",
                    "scrap_units",
                    "backlog_orders",
                    "labor_hours",
                ],
            },
            {
                "name": "OrderServiceLevels",
                "grain": "One row per order",
                "path": "data/raw/order_service_levels.csv",
                "columns": [
                    "order_id",
                    "order_date",
                    "site_code",
                    "customer_tier",
                    "channel",
                    "promised_cycle_hours",
                    "actual_cycle_hours",
                    "shipped_on_time",
                    "perfect_order_flag",
                    "root_cause",
                    "order_value_usd",
                ],
            },
            {
                "name": "QualityIncidents",
                "grain": "One row per operational incident",
                "path": "data/raw/quality_incidents.csv",
                "columns": [
                    "incident_id",
                    "opened_on",
                    "site_code",
                    "category",
                    "severity",
                    "resolution_hours",
                    "impacted_units",
                    "impacted_orders",
                ],
            },
            {
                "name": "SitePerformanceScorecard",
                "grain": "One row per site",
                "path": "data/processed/site_performance_scorecard.csv",
                "columns": scorecard.columns.tolist(),
            },
            {
                "name": "NetworkAlerts",
                "grain": "One row per elevated site alert",
                "path": "data/processed/network_alerts.csv",
                "columns": alerts.columns.tolist(),
            },
        ],
        "relationships": [
            {"from": "SiteDimension.site_code", "to": "OperationsPerformanceDaily.site_code", "cardinality": "1:*"},
            {"from": "SiteDimension.site_code", "to": "OrderServiceLevels.site_code", "cardinality": "1:*"},
            {"from": "SiteDimension.site_code", "to": "QualityIncidents.site_code", "cardinality": "1:*"},
            {"from": "SiteDimension.site_code", "to": "SitePerformanceScorecard.site_code", "cardinality": "1:1"},
            {"from": "SiteDimension.site_code", "to": "NetworkAlerts.site_code", "cardinality": "1:*"},
        ],
        "recommended_report_pages": [
            "Network Command Center",
            "Site Performance Deep Dive",
            "Service Risk and Delay Drivers",
            "Quality and Incident Response",
            "Capacity, Labor, and Recovery Planning",
        ],
        "refresh_strategy": {
            "landing_zone": "Daily flat-file drop or warehouse extracts",
            "refresh_frequency": "Hourly for operational review, daily for executive scorecards",
            "data_quality_checks": [
                "Duplicate order ID detection",
                "Null site-key validation",
                "Negative labor or volume value checks",
                "Outlier monitoring for downtime and backlog spikes",
            ],
        },
    }


def build_dashboard_blueprint(snapshot: dict[str, object], alerts: pd.DataFrame) -> str:
    attention_sites = ", ".join(alerts["site_name"].head(3).tolist()) if not alerts.empty else "No high-priority sites"
    return dedent(
        f"""\
        # Dashboard Blueprint

        ## Page 1 - Network Command Center

        - KPI cards for network score, throughput attainment, on-time service, perfect-order rate, revenue at risk, and expedite share
        - Regional heatmap by site with conditional formatting on composite score
        - Trend chart for throughput attainment and availability over time
        - Priority banner calling out: {attention_sites}

        ## Page 2 - Site Performance Deep Dive

        - Site selector with role, region, and automation tier filters
        - Variance waterfall for plan versus actual throughput
        - Scatter plot for productivity versus backlog pressure
        - Ranked table for site scorecards and executive priorities

        ## Page 3 - Service Risk

        - Delay driver Pareto using `root_cause`
        - Channel and customer-tier service breakdown
        - Revenue-at-risk trend and expedited-order concentration

        ## Page 4 - Quality and Incident Response

        - Incident severity trend
        - Resolution-time distribution
        - Root-cause matrix by workstream and category

        ## Page 5 - Capacity and Recovery Planning

        - Labor hours, overtime, and downtime trend
        - Scenario view for backlog burn-down
        - Executive commentary panel populated from the generated brief

        ## Narrative Anchor

        The dashboard should help leadership decide where to stabilize flow, where to add automation or staffing, and where service-risk exposure is starting to threaten revenue.
        """
    )


def build_dashboard_preview_html(snapshot: dict[str, object], alerts: pd.DataFrame) -> str:
    alert_lines = "".join(
        f"<li><strong>{row.site_name}</strong> - {row.risk_signal} ({row.recommended_action})</li>"
        for row in alerts.head(5).itertuples(index=False)
    )
    if not alert_lines:
        alert_lines = "<li>No active alerts.</li>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Operations Intelligence Hub - Dashboard Preview</title>
  <style>
    body {{
      margin: 0;
      font-family: "Segoe UI", sans-serif;
      background: #132029;
      color: #f6f0e7;
    }}
    .hero {{
      padding: 32px 40px 18px;
      background:
        radial-gradient(circle at top right, rgba(238, 186, 47, 0.18), transparent 30%),
        linear-gradient(135deg, #153543, #09131a 70%);
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 36px;
    }}
    .sub {{
      max-width: 780px;
      line-height: 1.6;
      color: #d8d6d1;
    }}
    .board {{
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 16px;
      padding: 18px 40px 40px;
    }}
    .panel {{
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 20px;
      padding: 20px;
      backdrop-filter: blur(10px);
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 12px;
    }}
    .metric {{
      background: rgba(255, 255, 255, 0.05);
      border-radius: 16px;
      padding: 16px;
    }}
    .metric span {{
      display: block;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: #c9b690;
      margin-bottom: 8px;
    }}
    .metric strong {{
      font-size: 28px;
    }}
    ul {{
      line-height: 1.8;
      padding-left: 20px;
    }}
  </style>
</head>
<body>
  <section class="hero">
    <h1>Operations Intelligence Hub</h1>
    <p class="sub">Static preview for the Power BI command center. The live report should preserve this narrative: score the network, isolate risk concentration, and turn operational telemetry into leadership decisions.</p>
  </section>
  <section class="board">
    <div class="panel">
      <h2>Executive Signals</h2>
      <div class="grid">
        <div class="metric"><span>Network Score</span><strong>{snapshot["network_score"]}</strong></div>
        <div class="metric"><span>On-Time Service</span><strong>{snapshot["on_time_service_pct"]}%</strong></div>
        <div class="metric"><span>Revenue At Risk</span><strong>${snapshot["revenue_at_risk_usd"]:,.0f}</strong></div>
        <div class="metric"><span>Perfect Order</span><strong>{snapshot["perfect_order_pct"]}%</strong></div>
        <div class="metric"><span>Critical Sites</span><strong>{snapshot["critical_sites"]}</strong></div>
        <div class="metric"><span>Expedite Share</span><strong>{snapshot["expedite_share_pct"]}%</strong></div>
      </div>
    </div>
    <div class="panel">
      <h2>Priority Actions</h2>
      <ul>{alert_lines}</ul>
    </div>
  </section>
</body>
</html>
"""


def build_theme_json() -> dict[str, object]:
    return {
        "name": "Operations Intelligence Hub",
        "dataColors": ["#035e7b", "#f0ad4e", "#7c3aed", "#228b22", "#d1495b", "#2f4858"],
        "background": "#f4f1ea",
        "foreground": "#17202a",
        "tableAccent": "#035e7b",
        "visualStyles": {
            "*": {
                "*": {
                    "title": [{"color": {"solid": {"color": "#17202a"}}, "fontSize": 13, "fontFamily": "Segoe UI Semibold"}],
                }
            }
        },
    }


def run_reporting_pipeline(paths: ProjectPaths) -> dict[str, object]:
    site_dimension = pd.read_csv(paths.site_dimension_path)
    operations = pd.read_csv(paths.operations_path)
    orders = pd.read_csv(paths.orders_path)
    incidents = pd.read_csv(paths.incidents_path)

    scorecard = build_site_scorecard(
        site_dimension=site_dimension,
        operations=operations,
        orders=orders,
        incidents=incidents,
    )
    alerts = build_network_alerts(scorecard)
    root_causes = build_root_cause_summary(orders, incidents)
    snapshot = build_kpi_snapshot(scorecard, operations, orders, alerts)
    executive_brief = build_executive_brief(snapshot, scorecard, alerts, root_causes)
    executive_html = build_executive_html(snapshot, scorecard, alerts, root_causes)
    semantic_model = build_semantic_model(scorecard, alerts, snapshot)
    dashboard_blueprint = build_dashboard_blueprint(snapshot, alerts)
    dashboard_preview_html = build_dashboard_preview_html(snapshot, alerts)

    scorecard.to_csv(paths.scorecard_path, index=False)
    alerts.to_csv(paths.alerts_path, index=False)
    root_causes.to_csv(paths.root_cause_path, index=False)
    paths.executive_snapshot_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    paths.executive_brief_path.write_text(executive_brief, encoding="utf-8")
    paths.executive_html_path.write_text(executive_html, encoding="utf-8")
    paths.measures_path.write_text(build_measures_dax(), encoding="utf-8")
    paths.semantic_model_path.write_text(json.dumps(semantic_model, indent=2), encoding="utf-8")
    paths.dashboard_blueprint_path.write_text(dashboard_blueprint, encoding="utf-8")
    paths.dashboard_preview_path.write_text(dashboard_preview_html, encoding="utf-8")
    paths.theme_path.write_text(json.dumps(build_theme_json(), indent=2), encoding="utf-8")

    return {
        "sites": int(scorecard.shape[0]),
        "alerts": int(alerts.shape[0]),
        "network_score": snapshot["network_score"],
        "top_priority_site": snapshot["top_priority_site"],
        "outputs": {
            "scorecard_path": str(paths.scorecard_path),
            "alerts_path": str(paths.alerts_path),
            "executive_snapshot_path": str(paths.executive_snapshot_path),
            "root_cause_path": str(paths.root_cause_path),
            "executive_brief_path": str(paths.executive_brief_path),
            "executive_html_path": str(paths.executive_html_path),
            "semantic_model_path": str(paths.semantic_model_path),
            "dashboard_preview_path": str(paths.dashboard_preview_path),
        },
    }
