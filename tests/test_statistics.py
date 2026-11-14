"""Regression tests for PSEG signed meters and recorder backfill continuity."""
import asyncio
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).parents[1] / "custom_components/psegli/statistics.py"
spec = importlib.util.spec_from_file_location("pseg_statistics", SOURCE)
pseg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pseg)


def series(values, *, start=None):
    start = start or datetime(2026, 8, 15, 12, tzinfo=pseg.LOCAL_TIME)
    return {"valid_points": [{"timestamp": start + timedelta(hours=i), "value": value}
                             for i, value in enumerate(values)]}


def august_15():
    return {
        "Meter #123g (194) - Off-Peak": series([-4.2, -3.876, -3.348]),
        "Meter #123 (194) - Off-Peak": series([0.012, 0.048, 0.504]),
        "Temperature": series([76, 75, 75]),
    }


class DirectionTests(unittest.TestCase):
    def test_date_windows_cover_history_without_overlap_or_truncation(self):
        start = datetime(2026, 4, 4, 12)
        end = datetime(2026, 9, 26, 18)
        windows = list(pseg.date_windows(start, end))
        self.assertEqual(windows[0][0].date(), start.date())
        self.assertEqual(windows[-1][1].date(), end.date())
        for first, last in windows:
            self.assertLessEqual((last - first).days, 27)
        for previous, following in zip(windows, windows[1:]):
            self.assertEqual(previous[1] + timedelta(days=1), following[0])
        self.assertEqual(sum((last - first).days + 1 for first, last in windows), 176)

    def test_date_windows_keep_a_single_day(self):
        day = datetime(2026, 8, 15)
        self.assertEqual(list(pseg.date_windows(day, day)), [(day, day)])

    def test_reversed_date_window_fails(self):
        with self.assertRaises(ValueError):
            list(pseg.date_windows(datetime(2026, 8, 16), datetime(2026, 8, 15)))

    def test_august_15_preserves_gross_import_and_export(self):
        grouped = pseg.directional_points(august_15())
        self.assertEqual(set(grouped), {"psegli:off_peak_usage", "psegli:off_peak_export"})
        self.assertAlmostEqual(sum(v for _, v in grouped["psegli:off_peak_export"]), 11.424)
        self.assertAlmostEqual(sum(v for _, v in grouped["psegli:off_peak_usage"]), 0.564)

    def test_exports_only_cannot_rewrite_imports(self):
        grouped = pseg.directional_points(august_15(), exports_only=True)
        self.assertEqual(set(grouped), {"psegli:off_peak_export"})

    def test_zero_export_night_retains_statistic(self):
        grouped = pseg.directional_points({"Meter #123g - On-Peak": series([0, 0])})
        rows = pseg.cumulative_rows(grouped["psegli:on_peak_export"], 25)
        self.assertEqual([r["sum"] for r in rows], [25, 25])

    def test_multiple_meters_are_summed_once_per_hour(self):
        grouped = pseg.directional_points({"Meter #1g - Off-Peak": series([-1]),
                                          "Meter #2g - Off-Peak": series([-2])})
        self.assertEqual([v for _, v in grouped["psegli:off_peak_export"]], [3])

    def test_unexpected_sign_fails_instead_of_silently_discarding_energy(self):
        for name, value in [("Meter #1g - Off-Peak", 1), ("Meter #1 - Off-Peak", -1)]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                pseg.directional_points({name: series([value])})

    def test_nonfinite_energy_is_rejected(self):
        for value in [float("nan"), float("inf"), -float("inf")]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                pseg.directional_points({"Meter #1 - Off-Peak": series([value])})

    def test_duplicate_hour_is_rejected(self):
        item = series([1]); item["valid_points"] *= 2
        with self.assertRaises(ValueError):
            pseg.directional_points({"Meter #1 - Off-Peak": item})

    def test_unsorted_points_are_sorted(self):
        item = series([1, 2]); item["valid_points"].reverse()
        points = pseg.directional_points({"Meter #1 - Off-Peak": item})["psegli:off_peak_usage"]
        self.assertEqual([r["sum"] for r in pseg.cumulative_rows(points, 10)], [11, 13])

    def test_wall_clock_conversion_handles_summer_and_winter(self):
        for month, utc_hour in [(8, 16), (1, 17)]:
            encoded = datetime(2026, month, 15, 12, tzinfo=timezone.utc).timestamp() * 1000
            value = pseg.portal_timestamp(encoded)
            self.assertEqual(value.hour, 12)
            self.assertEqual(value.astimezone(timezone.utc).hour, utc_hour)

    def test_nonhourly_and_naive_times_are_rejected(self):
        for start in [datetime(2026, 8, 15, 12),
                      datetime(2026, 8, 15, 12, 15, tzinfo=pseg.LOCAL_TIME)]:
            with self.subTest(start=start), self.assertRaises(ValueError):
                pseg.directional_points({"Meter #1 - Off-Peak": series([1], start=start)})


class RecorderTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.rows = {}
        self.queued = []
        self.events = []
        self.fail_read = False
        self.recorder = types.SimpleNamespace(async_block_till_done=self.drain,
                                             async_add_executor_job=self.execute)
        module_names = ["homeassistant", "homeassistant.components",
                        "homeassistant.components.recorder",
                        "homeassistant.components.recorder.models",
                        "homeassistant.components.recorder.statistics"]
        modules = {name: types.ModuleType(name) for name in module_names}
        modules[module_names[2]].get_instance = lambda hass: self.recorder
        modules[module_names[3]].StatisticMeanType = types.SimpleNamespace(NONE=0)
        modules[module_names[4]].statistics_during_period = self.read
        modules[module_names[4]].async_add_external_statistics = self.enqueue
        self.patcher = patch.dict(sys.modules, modules)
        self.patcher.start(); self.addCleanup(self.patcher.stop)

    async def drain(self):
        self.events.append("commit")
        for metadata, rows in self.queued:
            target = self.rows.setdefault(metadata["statistic_id"], {})
            target.update({r["start"].timestamp(): r["sum"] for r in rows})
        self.queued.clear()

    async def execute(self, fn, *args):
        return fn(*args)

    def read(self, hass, start, end, ids, period, units, types_):
        self.events.append("read")
        if self.fail_read:
            raise RuntimeError("Recorder unavailable")
        return {key: [{"start": ts, "sum": value} for ts, value in self.rows.get(key, {}).items()
                      if start.timestamp() <= ts < end.timestamp()] for key in ids}

    def enqueue(self, hass, metadata, rows):
        self.assertEqual(metadata["mean_type"], 0)
        self.assertEqual(metadata["unit_class"], "energy")
        self.events.append("enqueue")
        self.queued.append((metadata, rows))

    async def test_overlap_is_idempotent_and_waits_for_commits(self):
        await pseg.async_import_usage(None, august_15())
        expected = {k: dict(v) for k, v in self.rows.items()}
        await pseg.async_import_usage(None, august_15())
        self.assertEqual(self.rows, expected)
        self.assertFalse(self.queued)
        self.assertEqual(self.events[0], "commit")
        self.assertEqual(self.events[-1], "commit")

    async def test_new_export_statistic_counts_its_first_hour(self):
        await pseg.async_import_usage(None, august_15(), exports_only=True)
        rows = sorted(self.rows["psegli:off_peak_export"].items())
        self.assertEqual(rows[0][1], 0)
        self.assertEqual(rows[1][0] - rows[0][0], 3600)
        self.assertAlmostEqual(rows[1][1] - rows[0][1], 4.2)

    async def test_long_inactive_export_gap_preserves_offset(self):
        earlier = datetime(2026, 6, 1, tzinfo=timezone.utc).timestamp()
        self.rows["psegli:off_peak_export"] = {earlier: 100}
        await pseg.async_import_usage(None, august_15(), exports_only=True)
        self.assertAlmostEqual(self.rows["psegli:off_peak_export"][max(self.rows["psegli:off_peak_export"])], 111.424)
        self.assertNotIn("psegli:off_peak_usage", self.rows)

    async def test_offset_reads_include_previously_queued_data(self):
        previous = datetime(2026, 8, 15, 11, tzinfo=pseg.LOCAL_TIME)
        self.queued.append(({"statistic_id": "psegli:off_peak_export"},
                            [{"start": previous, "sum": 50}]))
        await pseg.async_import_usage(None, august_15(), exports_only=True)
        self.assertAlmostEqual(max(self.rows["psegli:off_peak_export"].values()), 61.424)

    async def test_failed_offset_lookup_writes_nothing(self):
        self.fail_read = True
        with self.assertRaises(RuntimeError):
            await pseg.async_import_usage(None, august_15())
        self.assertEqual(self.rows, {})
        self.assertFalse(self.queued)

    async def test_invalid_second_series_does_not_partially_import(self):
        chart = august_15(); chart["Meter #123 - On-Peak"] = series([-3])
        with self.assertRaises(ValueError):
            await pseg.async_import_usage(None, chart)
        self.assertEqual(self.rows, {})

    async def test_older_recorder_retains_legacy_metadata(self):
        del sys.modules["homeassistant.components.recorder.models"].StatisticMeanType
        captured = []
        def enqueue(hass, metadata, rows):
            captured.append(metadata)
            self.queued.append((metadata, rows))
        with patch.object(sys.modules["homeassistant.components.recorder.statistics"],
                          "async_add_external_statistics", enqueue):
            await pseg.async_import_usage(None, august_15())
        self.assertTrue(captured)
        for metadata in captured:
            self.assertFalse(metadata["has_mean"])
            self.assertNotIn("mean_type", metadata)


if __name__ == "__main__":
    unittest.main()
