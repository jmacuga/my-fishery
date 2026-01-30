import unittest
import asyncio
import json
from unittest.mock import patch, AsyncMock, Mock
from pathlib import Path
import sys

# allow importing from src
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.water_caretaker_agent import WaterCaretakerAgent


class TestWaterCaretakerAgentInit(unittest.TestCase):
    def test_initial_state(self):
        agent = WaterCaretakerAgent("water@localhost", "pw", "owner@localhost")
        self.assertEqual(agent.owner_jid, "owner@localhost")
        self.assertEqual(agent.ph_data, [])
        self.assertEqual(agent.last_values, 10)
        self.assertAlmostEqual(agent.z_score_alert, 1.1)


class TestWaterQualityBehaviour(unittest.TestCase):
    def setUp(self):
        self.agent = WaterCaretakerAgent("water@localhost", "pw", "owner@localhost")
        self.behaviour = self.agent.WaterQualityMeasureBehaviour(period=1)
        self.behaviour.agent = self.agent

    @patch("src.misc.get_random_data")
    @patch.object(
        WaterCaretakerAgent.WaterQualityMeasureBehaviour,
        "calculate_quality",
        new_callable=AsyncMock,
    )
    def test_collect_data_appends_and_calls_calculate(self, mock_calc, mock_get):
        mock_get.return_value = 7.5

        async def run_once():
            await self.behaviour.collect_data()

        asyncio.run(run_once())

        self.assertEqual(len(self.agent.ph_data), 1)
        self.assertEqual(self.agent.ph_data[0], 7.5)
        mock_calc.assert_awaited()

    @patch("src.misc.calculate_z_score")
    async def _call_calculate_quality(self, mock_calc, return_value):
        mock_calc.return_value = return_value
        await self.behaviour.calculate_quality()

    @patch("src.misc.calculate_z_score")
    def test_calculate_quality_no_zscore(self, mock_calc):
        mock_calc.return_value = None

        async def run_test():
            # should not raise and not call send_water_quality_alarm
            self.behaviour.send_water_quality_alarm = AsyncMock()
            await self.behaviour.calculate_quality()
            self.behaviour.send_water_quality_alarm.assert_not_awaited()

        asyncio.run(run_test())

    @patch("src.misc.calculate_z_score")
    def test_calculate_quality_below_alert(self, mock_calc):
        # z_score smaller than alert threshold (abs <= 1.1)
        mock_calc.return_value = 0.5

        async def run_test():
            self.behaviour.send_water_quality_alarm = AsyncMock()
            await self.behaviour.calculate_quality()
            self.behaviour.send_water_quality_alarm.assert_not_awaited()

        asyncio.run(run_test())

    @patch("src.water_caretaker_agent.calculate_z_score")
    def test_calculate_quality_exceeds_alert(self, mock_calc):
        # z_score greater than alert threshold
        mock_calc.return_value = 2.3456

        async def run_test():
            self.behaviour.send_water_quality_alarm = AsyncMock()
            await self.behaviour.calculate_quality()
            # should be called with rounded value
            self.behaviour.send_water_quality_alarm.assert_awaited()
            called_args = self.behaviour.send_water_quality_alarm.await_args[0]
            self.assertAlmostEqual(called_args[0], round(2.3456, 2))

        asyncio.run(run_test())

    def test_send_water_quality_alarm_sends_and_aerates(self):
        async def run_test():
            # prepare behaviour state
            self.agent.ph_data = [7.1, 7.2]
            self.behaviour.send = AsyncMock()
            self.behaviour.aeration = AsyncMock()

            await self.behaviour.send_water_quality_alarm(0.77)

            # ensure a message has been sent
            self.behaviour.send.assert_awaited()
            sent_msg = self.behaviour.send.await_args[0][0]
            # message body should be JSON containing z_score and ph_data
            payload = json.loads(sent_msg.body)
            self.assertIn("z_score", payload)
            self.assertIn("ph_data", payload)

            # aeration should be awaited after sending
            self.behaviour.aeration.assert_awaited()

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
