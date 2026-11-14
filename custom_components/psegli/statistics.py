"""Separate PSEG's consumption and signed generation meters for Energy."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
import math
import re
from zoneinfo import ZoneInfo

LOCAL_TIME = ZoneInfo("America/New_York")
GENERATION_METER = re.compile(r"^Meter\s+#\S+g(?:\s|$)", re.IGNORECASE)


def date_windows(start: datetime, end: datetime):
    """Inclusive date ranges below PSEG's silent hourly-response limit."""
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    end = end.replace(hour=0, minute=0, second=0, microsecond=0)
    if start > end:
        raise ValueError("Start date is after end date")
    while start <= end:
        window_end = min(start + timedelta(days=27), end)
        yield start, window_end
        start = window_end + timedelta(days=1)


def portal_timestamp(milliseconds: float) -> datetime:
    """PSEG encodes local wall-clock labels as UTC, including in its CSV."""
    return datetime.fromtimestamp(milliseconds / 1000, timezone.utc).replace(
        tzinfo=LOCAL_TIME
    )


def directional_points(chart_data: dict, *, exports_only: bool = False) -> dict:
    """Aggregate meters once per tariff/direction without netting imports."""
    grouped = defaultdict(lambda: defaultdict(float))
    for name, series in chart_data.items():
        tariff = "off_peak" if "Off-Peak" in name else "on_peak" if "On-Peak" in name else None
        if tariff is None:
            continue
        exporting = bool(GENERATION_METER.search(name))
        if exports_only and not exporting:
            continue
        statistic_id = f"psegli:{tariff}_{'export' if exporting else 'usage'}"
        seen = set()
        for point in series.get("valid_points", []):
            timestamp = point["timestamp"]
            if timestamp.tzinfo is None:
                raise ValueError(f"Naive timestamp in {name}")
            timestamp = timestamp.astimezone(timezone.utc)
            if timestamp.minute or timestamp.second or timestamp.microsecond:
                raise ValueError(f"Non-hourly timestamp in {name}")
            if timestamp in seen:
                raise ValueError(f"Duplicate hour in {name}: {timestamp}")
            seen.add(timestamp)
            value = float(point["value"])
            if not math.isfinite(value):
                raise ValueError(f"Non-finite energy in {name}")
            energy = -value if exporting else value
            if energy < 0:
                raise ValueError(f"Unexpected energy direction in {name}: {value}")
            # Keep zero hours: a night/week with no exports must not reset sums.
            grouped[statistic_id][timestamp] += energy
    return {key: sorted(points.items()) for key, points in grouped.items() if points}


def cumulative_rows(points: list, offset: float) -> list:
    """Build monotonically increasing sums from sorted hourly energy."""
    if not math.isfinite(offset) or offset < 0:
        raise ValueError("Invalid cumulative offset")
    rows = []
    for start, energy in points:
        offset += energy
        rows.append({"start": start, "sum": offset})
    return rows


async def async_import_usage(hass, chart_data: dict, *, exports_only: bool = False):
    """Import under the caller's lock and wait for recorder commits."""
    from homeassistant.components.recorder import get_instance
    try:
        from homeassistant.components.recorder.models import StatisticMeanType
    except ImportError:  # Keep the integration's existing minimum HA version.
        mean_metadata = {"has_mean": False}
    else:
        mean_metadata = {"mean_type": StatisticMeanType.NONE, "unit_class": "energy"}
    from homeassistant.components.recorder.statistics import (
        async_add_external_statistics,
        statistics_during_period,
    )

    recorder = get_instance(hass)
    grouped = directional_points(chart_data, exports_only=exports_only)
    if not grouped:
        raise ValueError("PSEG returned no matching energy series")
    # Offset lookups must see previous imports, including those queued elsewhere.
    await recorder.async_block_till_done()
    pending = []
    for statistic_id, points in grouped.items():
        first = points[0][0]
        # A generation meter can be inactive for longer than seven days.
        previous = await recorder.async_add_executor_job(
            statistics_during_period, hass, datetime(1970, 1, 1, tzinfo=timezone.utc),
            first, {statistic_id}, "hour", None, {"sum"},
        )
        before = [row for row in previous.get(statistic_id, [])
                  if row["start"] < first.timestamp() and row.get("sum") is not None]
        offset = max(before, key=lambda row: row["start"])["sum"] if before else 0.0
        rows = cumulative_rows(points, offset)
        if not before:
            # Energy calculates differences between sums. Anchor a new series
            # so its first measured hour is included in consumption/export.
            rows.insert(0, {"start": first - timedelta(hours=1), "sum": 0.0})
        label = statistic_id.split(":", 1)[1].replace("_", " ").title()
        metadata = {
            "statistic_id": statistic_id, "source": "psegli",
            "unit_of_measurement": "kWh", "has_sum": True,
            **mean_metadata,
            "name": f"PSEG {label}",
        }
        pending.append((metadata, rows))
    # Validate every series and resolve every offset before queuing any writes.
    for metadata, rows in pending:
        async_add_external_statistics(hass, metadata, rows)
    await recorder.async_block_till_done()
    return {metadata["statistic_id"]: len(rows) for metadata, rows in pending}
