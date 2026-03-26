from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from random import Random

import pandas as pd


@dataclass(frozen=True)
class SiteProfile:
    site_code: str
    site_name: str
    region: str
    country: str
    automation_tier: str
    network_role: str
    daily_capacity: int
    productivity_index: float
    quality_baseline: float
    reliability_baseline: float
    service_target: float


SITE_CATALOG = [
    SiteProfile("ATL-01", "Atlanta Fulfillment Center", "North America", "United States", "High", "Retail and eCommerce", 1280, 37.0, 0.988, 0.955, 0.972),
    SiteProfile("CHI-02", "Chicago Distribution Campus", "North America", "United States", "Medium", "B2B and Retail", 1160, 35.5, 0.985, 0.949, 0.968),
    SiteProfile("DAL-03", "Dallas Omni-Channel Hub", "North America", "United States", "High", "Omni-Channel", 1320, 38.4, 0.989, 0.957, 0.974),
    SiteProfile("MEX-01", "Monterrey Export Gateway", "Latin America", "Mexico", "Medium", "Cross-Border", 980, 32.2, 0.981, 0.941, 0.955),
    SiteProfile("FRA-01", "Frankfurt Regional Hub", "Europe", "Germany", "High", "Continental Distribution", 1180, 36.6, 0.987, 0.953, 0.971),
    SiteProfile("MAD-02", "Madrid Service Center", "Europe", "Spain", "Medium", "Southern Europe", 940, 31.9, 0.983, 0.944, 0.962),
    SiteProfile("LHR-03", "Milton Keynes Network Center", "Europe", "United Kingdom", "High", "Returns and Reverse Logistics", 1100, 34.8, 0.984, 0.947, 0.965),
    SiteProfile("DXB-01", "Dubai Regional Gateway", "Middle East", "United Arab Emirates", "Medium", "Cross-Region Routing", 890, 30.6, 0.982, 0.942, 0.958),
    SiteProfile("JHB-01", "Johannesburg Service Hub", "Africa", "South Africa", "Low", "Emerging Market Coverage", 760, 27.8, 0.976, 0.931, 0.948),
    SiteProfile("BLR-01", "Bengaluru Fulfillment Center", "Asia Pacific", "India", "Medium", "Consumer Electronics", 1140, 34.2, 0.985, 0.948, 0.966),
    SiteProfile("SIN-01", "Singapore Control Tower", "Asia Pacific", "Singapore", "High", "Express and Critical Parts", 860, 33.8, 0.99, 0.962, 0.981),
    SiteProfile("SYD-01", "Sydney Service Campus", "Asia Pacific", "Australia", "Medium", "Aftermarket and Service", 820, 29.7, 0.982, 0.943, 0.959),
]

SHIFT_FACTORS = {
    "Day": 1.0,
    "Swing": 0.93,
    "Night": 0.84,
}

WORKSTREAMS = {
    "Inbound": 0.26,
    "Fulfillment": 0.38,
    "Kitting": 0.18,
    "Returns": 0.18,
}

SERVICE_CHANNELS = ["Retail", "Marketplace", "Wholesale", "Strategic", "Field Service"]
DELAY_ROOT_CAUSES = [
    "Carrier capacity",
    "Inventory mismatch",
    "Labor coverage gap",
    "Supplier delay",
    "Weather disruption",
    "Slotting constraint",
    "Documentation hold",
    "Demand spike",
]
INCIDENT_CATEGORIES = [
    "Equipment reliability",
    "Inventory variance",
    "Process discipline",
    "Supplier quality",
    "Carrier exception",
    "Staffing instability",
]


def _seasonal_multiplier(current_date: date) -> float:
    if current_date.month in {10, 11, 12}:
        return 1.16
    if current_date.month in {6, 7, 8}:
        return 1.05
    if current_date.month in {1, 2}:
        return 0.96
    return 1.0


def _weekday_multiplier(current_date: date) -> float:
    weekday = current_date.weekday()
    if weekday in {0, 1}:
        return 1.04
    if weekday in {2, 3}:
        return 1.0
    if weekday == 4:
        return 1.06
    if weekday == 5:
        return 0.88
    return 0.82


def build_site_dimension(site_count: int | None = None) -> pd.DataFrame:
    selected_profiles = SITE_CATALOG[:site_count] if site_count else SITE_CATALOG
    rows = [
        {
            "site_code": profile.site_code,
            "site_name": profile.site_name,
            "region": profile.region,
            "country": profile.country,
            "automation_tier": profile.automation_tier,
            "network_role": profile.network_role,
            "daily_capacity": profile.daily_capacity,
            "productivity_index": round(profile.productivity_index, 2),
            "quality_target": round(profile.quality_baseline, 4),
            "reliability_target": round(profile.reliability_baseline, 4),
            "service_target": round(profile.service_target, 4),
        }
        for profile in selected_profiles
    ]
    return pd.DataFrame(rows)


def generate_sample_inputs(
    *,
    days: int = 365,
    site_count: int = 12,
    orders_per_site_day: int = 28,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rng = Random(seed)
    profiles = SITE_CATALOG[:site_count]
    start_date = date(2025, 1, 1)

    site_dimension = build_site_dimension(site_count)
    operations_rows: list[dict[str, object]] = []
    incident_rows: list[dict[str, object]] = []
    incident_id = 1

    for day_offset in range(days):
        current_date = start_date + timedelta(days=day_offset)
        seasonal = _seasonal_multiplier(current_date)
        weekday_factor = _weekday_multiplier(current_date)

        for profile in profiles:
            regional_pressure = 0.02 if profile.region in {"Latin America", "Africa"} else 0.0
            automation_relief = 0.02 if profile.automation_tier == "High" else 0.0

            for shift_name, shift_factor in SHIFT_FACTORS.items():
                for workstream, stream_mix in WORKSTREAMS.items():
                    planned_units = int(
                        profile.daily_capacity
                        * stream_mix
                        * shift_factor
                        * seasonal
                        * weekday_factor
                        * rng.uniform(0.94, 1.08)
                    )
                    available_minutes = 480
                    downtime_minutes = int(
                        max(
                            8,
                            (1 - profile.reliability_baseline + regional_pressure - automation_relief) * 240
                            + rng.gammavariate(2.6, 7.8)
                            + (10 if shift_name == "Night" else 0)
                            + (7 if workstream == "Returns" else 0),
                        )
                    )
                    availability_ratio = max(0.78, min(0.99, 1 - downtime_minutes / available_minutes))
                    performance_ratio = max(
                        0.73,
                        min(
                            0.99,
                            0.9
                            + availability_ratio * 0.06
                            - regional_pressure
                            + automation_relief
                            - (0.02 if shift_name == "Night" else 0)
                            + rng.uniform(-0.03, 0.03),
                        ),
                    )
                    actual_units = int(planned_units * performance_ratio)
                    first_pass_yield = max(
                        0.92,
                        min(
                            0.997,
                            profile.quality_baseline
                            - regional_pressure * 0.5
                            - (0.007 if workstream == "Returns" else 0)
                            + rng.uniform(-0.009, 0.004),
                        ),
                    )
                    scrap_units = max(1, int(actual_units * (1 - first_pass_yield)))
                    backlog_orders = max(
                        0,
                        int(
                            max(planned_units - actual_units, 0) * 0.14
                            + downtime_minutes * 0.28
                            + rng.uniform(0, 18),
                        ),
                    )
                    labor_hours = round(
                        (planned_units / max(profile.productivity_index, 1.0))
                        * (1.08 if shift_name != "Day" else 1.0)
                        * rng.uniform(0.97, 1.09),
                        1,
                    )
                    overtime_hours = round(
                        max(
                            0.0,
                            (planned_units - actual_units) / max(profile.productivity_index, 1.0) * 0.42
                            + rng.uniform(0.0, 5.0),
                        ),
                        1,
                    )
                    absenteeism_rate = round(
                        min(
                            0.14,
                            0.018
                            + regional_pressure * 0.3
                            + (0.012 if shift_name == "Night" else 0.0)
                            + rng.uniform(0.006, 0.032),
                        ),
                        4,
                    )
                    safety_near_misses = int(rng.random() < (0.014 + absenteeism_rate + downtime_minutes / 2600))
                    energy_cost_usd = round(
                        labor_hours * 7.4 + actual_units * 0.16 + downtime_minutes * 1.75 + rng.uniform(12.0, 68.0),
                        2,
                    )

                    operations_rows.append(
                        {
                            "date": current_date.isoformat(),
                            "site_code": profile.site_code,
                            "site_name": profile.site_name,
                            "region": profile.region,
                            "country": profile.country,
                            "shift": shift_name,
                            "workstream": workstream,
                            "planned_units": planned_units,
                            "actual_units": actual_units,
                            "available_minutes": available_minutes,
                            "downtime_minutes": downtime_minutes,
                            "scrap_units": scrap_units,
                            "backlog_orders": backlog_orders,
                            "labor_hours": labor_hours,
                            "overtime_hours": overtime_hours,
                            "absenteeism_rate": absenteeism_rate,
                            "safety_near_misses": safety_near_misses,
                            "energy_cost_usd": energy_cost_usd,
                        }
                    )

                    incident_probability = 0.003 + downtime_minutes / 5200 + backlog_orders / 9800 + absenteeism_rate * 0.08
                    incident_count = 1 if rng.random() < incident_probability else 0
                    if downtime_minutes > 78 and rng.random() < 0.18:
                        incident_count += 1

                    for incident_offset in range(incident_count):
                        severity_score = downtime_minutes + backlog_orders * 0.6 + safety_near_misses * 18 + incident_offset * 10
                        if severity_score > 95:
                            severity = "critical"
                        elif severity_score > 75:
                            severity = "high"
                        elif severity_score > 55:
                            severity = "medium"
                        else:
                            severity = "low"
                        incident_rows.append(
                            {
                                "incident_id": f"INC-{incident_id:07d}",
                                "opened_on": current_date.isoformat(),
                                "site_code": profile.site_code,
                                "site_name": profile.site_name,
                                "region": profile.region,
                                "workstream": workstream,
                                "category": rng.choice(INCIDENT_CATEGORIES),
                                "severity": severity,
                                "resolution_hours": round(rng.uniform(4.0, 28.0) * (1.4 if severity == "critical" else 1.0), 1),
                                "impacted_units": int(actual_units * rng.uniform(0.03, 0.12)),
                                "impacted_orders": int(backlog_orders * rng.uniform(0.18, 0.42)),
                                "owner_team": "Operations Excellence" if severity in {"critical", "high"} else "Site Leadership",
                            }
                        )
                        incident_id += 1

    operations = pd.DataFrame(operations_rows)
    incidents = pd.DataFrame(incident_rows)

    site_day_summary = (
        operations.groupby(["date", "site_code", "site_name", "region", "country"], as_index=False)
        .agg(
            planned_units=("planned_units", "sum"),
            actual_units=("actual_units", "sum"),
            downtime_minutes=("downtime_minutes", "sum"),
            backlog_orders=("backlog_orders", "sum"),
            labor_hours=("labor_hours", "sum"),
            overtime_hours=("overtime_hours", "sum"),
            scrap_units=("scrap_units", "sum"),
        )
    )

    order_rows: list[dict[str, object]] = []
    order_id = 1
    for row in site_day_summary.itertuples(index=False):
        pressure_ratio = (row.backlog_orders / max(row.planned_units, 1)) + (row.downtime_minutes / 2000)
        daily_order_count = max(
            10,
            int(
                orders_per_site_day
                + row.planned_units / 180
                + rng.randint(-3, 6)
                + (4 if row.region in {"Europe", "North America"} else 0),
            ),
        )

        for _ in range(daily_order_count):
            customer_tier = rng.choices(["Strategic", "Growth", "Core"], weights=[0.18, 0.37, 0.45], k=1)[0]
            channel = rng.choice(SERVICE_CHANNELS)
            promised_hours = rng.choices([12, 24, 36, 48, 72], weights=[0.12, 0.3, 0.2, 0.28, 0.1], k=1)[0]
            expedite_flag = int(rng.random() < 0.06 + pressure_ratio * 0.18)
            base_multiplier = 0.68 + pressure_ratio * 0.4 + (0.02 if channel == "Marketplace" else 0.0)
            actual_cycle_hours = round(promised_hours * min(1.35, max(0.66, base_multiplier + rng.uniform(-0.06, 0.14))), 1)
            if rng.random() < 0.035 + pressure_ratio * 0.18 + (0.025 if channel == "Marketplace" else 0.0):
                actual_cycle_hours = round(actual_cycle_hours + rng.uniform(2.0, min(18.0, promised_hours * 0.45)), 1)
            shipped_on_time = int(actual_cycle_hours <= promised_hours)
            delay_hours = round(max(actual_cycle_hours - promised_hours, 0.0), 1)
            damage_flag = int(rng.random() < 0.009 + pressure_ratio * 0.08)
            split_shipment_flag = int(rng.random() < 0.035 + pressure_ratio * 0.11)
            documentation_issue_flag = int(rng.random() < 0.007 + pressure_ratio * 0.06)
            perfect_order_flag = int(
                shipped_on_time == 1 and damage_flag == 0 and split_shipment_flag == 0 and documentation_issue_flag == 0
            )
            root_cause = "On-plan" if shipped_on_time == 1 else rng.choice(DELAY_ROOT_CAUSES)
            line_count = rng.randint(1, 8)
            order_value_usd = round(
                line_count
                * rng.uniform(155.0, 940.0)
                * (1.22 if customer_tier == "Strategic" else 1.0)
                * (1.08 if expedite_flag else 1.0),
                2,
            )

            order_rows.append(
                {
                    "order_id": f"ORD-{order_id:09d}",
                    "order_date": row.date,
                    "site_code": row.site_code,
                    "site_name": row.site_name,
                    "region": row.region,
                    "country": row.country,
                    "customer_tier": customer_tier,
                    "channel": channel,
                    "line_count": line_count,
                    "promised_cycle_hours": promised_hours,
                    "actual_cycle_hours": actual_cycle_hours,
                    "delay_hours": delay_hours,
                    "shipped_on_time": shipped_on_time,
                    "expedite_flag": expedite_flag,
                    "damage_flag": damage_flag,
                    "split_shipment_flag": split_shipment_flag,
                    "documentation_issue_flag": documentation_issue_flag,
                    "perfect_order_flag": perfect_order_flag,
                    "root_cause": root_cause,
                    "order_value_usd": order_value_usd,
                }
            )
            order_id += 1

    orders = pd.DataFrame(order_rows)
    return site_dimension, operations, orders, incidents


def write_inputs(
    *,
    site_dimension: pd.DataFrame,
    operations: pd.DataFrame,
    orders: pd.DataFrame,
    incidents: pd.DataFrame,
    site_dimension_path,
    operations_path,
    orders_path,
    incidents_path,
) -> None:
    site_dimension.to_csv(site_dimension_path, index=False)
    operations.to_csv(operations_path, index=False)
    orders.to_csv(orders_path, index=False)
    incidents.to_csv(incidents_path, index=False)
