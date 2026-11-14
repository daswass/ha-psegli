"""Exercise the existing writer against modern and legacy recorder metadata."""
import ast
from datetime import datetime, timedelta, timezone
import logging
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import AsyncMock, Mock, patch

import pytz


class MetadataTests(unittest.IsolatedAsyncioTestCase):
    async def test_metadata_contract_and_existing_sums(self):
        source = Path(__file__).parents[1] / "custom_components/psegli/__init__.py"
        tree = ast.parse(source.read_text())
        writer = next(node for node in tree.body if isinstance(node, ast.AsyncFunctionDef)
                      and node.name == "_process_chart_data")
        recorder_module = types.ModuleType("homeassistant.components.recorder.statistics")
        recorder_module.statistics_during_period = Mock()
        for modern in [True, False]:
            with self.subTest(modern=modern):
                mean_none = object()
                enqueue = Mock()
                recorder = types.SimpleNamespace(async_add_executor_job=AsyncMock(return_value={}))
                namespace = {
                    "HomeAssistant": object, "Any": object,
                    "datetime": datetime, "timedelta": timedelta, "timezone": timezone,
                    "pytz": pytz, "_LOGGER": logging.getLogger(__name__),
                    "StatisticMeanType": types.SimpleNamespace(NONE=mean_none) if modern else None,
                    "get_last_cumulative_kwh": AsyncMock(return_value=10.0),
                    "async_add_external_statistics": enqueue,
                    "get_instance": lambda hass: recorder,
                }
                exec(compile(ast.Module(body=[writer], type_ignores=[]), str(source), "exec"), namespace)
                hass = types.SimpleNamespace(async_add_executor_job=AsyncMock(return_value=timezone.utc))
                chart = {f"Meter #123 - {tariff}": {"valid_points": [
                    {"timestamp": datetime(2026, 11, 14, tzinfo=timezone.utc), "value": 1.25}
                ]} for tariff in ["Off-Peak", "On-Peak"]}
                with patch.dict(sys.modules, {recorder_module.__name__: recorder_module}):
                    await namespace[writer.name](hass, chart)
                self.assertEqual(enqueue.call_count, 2)
                ids = set()
                for call in enqueue.call_args_list:
                    _, metadata, rows = call.args
                    ids.add(metadata["statistic_id"])
                    self.assertEqual(rows[0]["sum"], 11.25)
                    self.assertTrue(metadata["has_sum"])
                    self.assertEqual(metadata["unit_of_measurement"], "kWh")
                    if modern:
                        self.assertIs(metadata["mean_type"], mean_none)
                        self.assertEqual(metadata["unit_class"], "energy")
                        self.assertNotIn("has_mean", metadata)
                    else:
                        self.assertFalse(metadata["has_mean"])
                        self.assertNotIn("mean_type", metadata)
                self.assertEqual(ids, {"psegli:off_peak_usage", "psegli:on_peak_usage"})


if __name__ == "__main__":
    unittest.main()
