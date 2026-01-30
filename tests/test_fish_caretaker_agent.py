import unittest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4

# Add the src directory to the path for imports
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.fish_caretaker_agent import FishCaretakerAgent
from src.protocols import Protocols


class TestFishCaretakerAgentInit(unittest.TestCase):
    """Test initialization of FishCaretakerAgent"""

    def test_agent_initialization(self):
        """Test that agent initializes with correct default values"""
        jid = "fish_caretaker@localhost"
        password = "password123"
        owner_jid = "owner@localhost"

        agent = FishCaretakerAgent(jid, password, owner_jid)

        self.assertEqual(agent.jid, jid)
        self.assertEqual(agent.owner_jid, owner_jid)
        self.assertEqual(agent.camera_data, [])
        self.assertEqual(agent.sonar_data, [])
        self.assertEqual(agent.fishes_taken, {})
        self.assertEqual(agent.z_score_needs_restocking_alarm_point, 0.5)
        self.assertEqual(agent.feeding_parameters, {"portion": 1, "interval_s": 2})
        self.assertEqual(agent.food_supplies_kg, 10.0)
        self.assertEqual(agent.required_food_supplies_kg, 2.0)
        self.assertFalse(agent.order_food_need)
        self.assertEqual(agent.order_amount_kg, 25.0)

    def test_feeding_update_event_initialized(self):
        """Test that feeding_update_event is an asyncio.Event"""
        agent = FishCaretakerAgent("test@localhost", "pass", "owner@localhost")
        self.assertIsInstance(agent.feeding_update_event, asyncio.Event)


class TestMonitorFishState(unittest.TestCase):
    """Test MonitorFishState behaviour"""

    def setUp(self):
        self.agent = FishCaretakerAgent("fish@localhost", "pass", "owner@localhost")
        self.behaviour = self.agent.MonitorFishState()
        self.behaviour.agent = self.agent

    def test_collect_camera_data_returns_non_negative(self):
        """Test that collect_camera_data returns non-negative values"""
        with patch("src.fish_caretaker_agent.get_random_data") as mock_random:
            mock_random.return_value = 15.0
            result = self.behaviour.collect_camera_data()
            self.assertGreaterEqual(result, 0)

    def test_collect_camera_data_handles_negative_random(self):
        """Test that collect_camera_data ensures non-negative result"""
        with patch("src.fish_caretaker_agent.get_random_data") as mock_random:
            mock_random.return_value = -5.0
            result = self.behaviour.collect_camera_data()
            self.assertEqual(result, 0)

    def test_collect_sonar_data_returns_non_negative(self):
        """Test that collect_sonar_data returns non-negative values"""
        with patch("src.fish_caretaker_agent.get_random_data") as mock_random:
            mock_random.return_value = 18.0
            result = self.behaviour.collect_sonar_data()
            self.assertGreaterEqual(result, 0)

    def test_collect_sonar_data_handles_negative_random(self):
        """Test that collect_sonar_data ensures non-negative result"""
        with patch("src.fish_caretaker_agent.get_random_data") as mock_random:
            mock_random.return_value = -10.0
            result = self.behaviour.collect_sonar_data()
            self.assertEqual(result, 0)

    @patch("src.fish_caretaker_agent.get_random_data")
    def test_monitor_fish_state_run(self, mock_random):
        """Test that run method appends data to camera and sonar lists"""
        mock_random.side_effect = [15.0, 20.0]  # camera_data, then sonar_data

        async def run_test():
            await self.behaviour.run()
            self.assertEqual(len(self.agent.camera_data), 1)
            self.assertEqual(len(self.agent.sonar_data), 1)

        asyncio.run(run_test())


class TestManageRestocking(unittest.TestCase):
    """Test ManageRestocking behaviour"""

    def setUp(self):
        self.agent = FishCaretakerAgent("fish@localhost", "pass", "owner@localhost")
        self.behaviour = self.agent.ManageRestocking()
        self.behaviour.agent = self.agent

    def test_if_needs_stocking_with_empty_data(self):
        """Test if_needs_stocking returns False when data is empty"""
        needs_stocking, z_score = self.behaviour.if_needs_stocking()
        self.assertFalse(needs_stocking)
        self.assertIsNone(z_score)

    def test_if_needs_stocking_with_single_data_point(self):
        """Test if_needs_stocking returns False with only one data point"""
        self.agent.camera_data = [15.0]
        self.agent.sonar_data = [16.0]

        needs_stocking, z_score = self.behaviour.if_needs_stocking()
        self.assertFalse(needs_stocking)
        self.assertIsNone(z_score)

    @patch("src.fish_caretaker_agent.calculate_z_score")
    def test_if_needs_stocking_high_z_score(self, mock_z_score):
        """Test if_needs_stocking when z-scores are high (no restocking needed)"""
        mock_z_score.side_effect = [0.8, 0.9]  # both above threshold

        self.agent.camera_data = [10.0, 11.0, 12.0]
        self.agent.sonar_data = [10.0, 11.0, 12.0]

        needs_stocking, z_score = self.behaviour.if_needs_stocking()
        self.assertFalse(needs_stocking)

    @patch("src.fish_caretaker_agent.calculate_z_score")
    def test_if_needs_stocking_low_z_score(self, mock_z_score):
        """Test if_needs_stocking when z-scores are low (restocking needed)"""
        mock_z_score.side_effect = [0.2, 0.3]  # both below threshold of 0.5

        self.agent.camera_data = [10.0, 11.0, 12.0]
        self.agent.sonar_data = [10.0, 11.0, 12.0]

        needs_stocking, z_score = self.behaviour.if_needs_stocking()
        self.assertTrue(needs_stocking)
        self.assertEqual(z_score, 0.3)  # max of the two

    @patch("src.fish_caretaker_agent.calculate_z_score")
    def test_if_needs_stocking_uses_max_z_score(self, mock_z_score):
        """Test that if_needs_stocking uses the maximum absolute z-score"""
        mock_z_score.side_effect = [0.3, 0.2]

        self.agent.camera_data = [10.0, 11.0, 12.0]
        self.agent.sonar_data = [10.0, 11.0, 12.0]

        needs_stocking, z_score = self.behaviour.if_needs_stocking()
        self.assertEqual(z_score, 0.3)

    @patch.object(FishCaretakerAgent.ManageRestocking, "send")
    @patch("src.fish_caretaker_agent.calculate_z_score")
    def test_send_needs_stocking_alarm(self, mock_z_score, mock_send):
        """Test that send_needs_stocking_alarm creates and sends a message"""
        mock_z_score.side_effect = [0.2, 0.3]
        mock_send.return_value = AsyncMock()

        self.agent.camera_data = [10.0, 11.0, 12.0]
        self.agent.sonar_data = [10.0, 11.0, 12.0]

        async def run_test():
            await self.behaviour.send_needs_stocking_alarm(0.3)

        asyncio.run(run_test())


class TestRegisterFishDataBehaviour(unittest.TestCase):
    """Test RegisterFishDataBehaviour"""

    def setUp(self):
        self.agent = FishCaretakerAgent("fish@localhost", "pass", "owner@localhost")
        self.behaviour = self.agent.RegisterFishDataBehaviour()
        self.behaviour.agent = self.agent

    @patch.object(FishCaretakerAgent.RegisterFishDataBehaviour, "receive")
    @patch.object(FishCaretakerAgent.RegisterFishDataBehaviour, "send")
    def test_register_fish_data_valid_message(self, mock_send, mock_receive):
        """Test fish data registration with valid message"""
        fish_data = {
            "species": "salmon",
            "size": "large",
            "mass": 5.0,
            "time": "2026-01-30 10:00:00",
        }

        msg = Mock()
        msg.sender = "fisher@localhost"
        msg.body = json.dumps(fish_data)
        msg.metadata = {
            "conversation-id": str(uuid4()),
            "reply-with": str(uuid4()),
        }
        msg.make_reply = Mock(return_value=Mock(metadata={}, body=""))

        mock_receive.return_value = msg
        mock_send.return_value = AsyncMock()

        async def run_test():
            await self.behaviour.run()

        asyncio.run(run_test())

        # Check if fish data was registered
        self.assertIn("fisher@localhost", self.agent.fishes_taken)

    @patch.object(FishCaretakerAgent.RegisterFishDataBehaviour, "receive")
    def test_register_fish_data_invalid_json(self, mock_receive):
        """Test fish data registration with invalid JSON"""
        msg = Mock()
        msg.sender = "fisher@localhost"
        msg.body = "invalid json"
        msg.metadata = {
            "conversation-id": str(uuid4()),
            "reply-with": str(uuid4()),
        }

        mock_receive.return_value = msg

        async def run_test():
            # Should not raise an exception
            await self.behaviour.run()

        asyncio.run(run_test())

    @patch.object(FishCaretakerAgent.RegisterFishDataBehaviour, "receive")
    def test_register_fish_data_no_message(self, mock_receive):
        """Test when no message is received"""
        mock_receive.return_value = None

        async def run_test():
            # Should handle gracefully when no message
            await self.behaviour.run()

        asyncio.run(run_test())


class TestFeedingBehaviour(unittest.TestCase):
    """Test FeedingBehaviour"""

    def setUp(self):
        self.agent = FishCaretakerAgent("fish@localhost", "pass", "owner@localhost")
        self.behaviour = self.agent.FeedingBehaviour(period=2)
        self.behaviour.agent = self.agent

    def test_feed_with_zero_portion(self):
        """Test that feed skips when portion is 0"""
        self.agent.feeding_parameters = {"portion": 0.0, "interval_s": 2}
        initial_supplies = self.agent.food_supplies_kg

        async def run_test():
            await self.behaviour.feed()
            self.assertEqual(self.agent.food_supplies_kg, initial_supplies)

        asyncio.run(run_test())

    def test_feed_with_negative_portion(self):
        """Test that feed skips when portion is negative"""
        self.agent.feeding_parameters = {"portion": -1.0, "interval_s": 2}
        initial_supplies = self.agent.food_supplies_kg

        async def run_test():
            await self.behaviour.feed()
            self.assertEqual(self.agent.food_supplies_kg, initial_supplies)

        asyncio.run(run_test())

    def test_feed_with_no_supplies(self):
        """Test that feed skips when no food supplies are left"""
        self.agent.feeding_parameters = {"portion": 1.0, "interval_s": 2}
        self.agent.food_supplies_kg = 0.0
        initial_supplies = self.agent.food_supplies_kg

        async def run_test():
            await self.behaviour.feed()
            self.assertEqual(self.agent.food_supplies_kg, initial_supplies)

        asyncio.run(run_test())

    def test_feed_normal_operation(self):
        """Test feed with normal portion and available supplies"""
        self.agent.feeding_parameters = {"portion": 2.0, "interval_s": 2}
        self.agent.food_supplies_kg = 10.0
        initial_supplies = self.agent.food_supplies_kg

        async def run_test():
            await self.behaviour.feed()
            self.assertEqual(self.agent.food_supplies_kg, initial_supplies - 2.0)

        asyncio.run(run_test())

    def test_feed_portion_exceeds_supplies(self):
        """Test feed when portion exceeds available supplies"""
        self.agent.feeding_parameters = {"portion": 5.0, "interval_s": 2}
        self.agent.food_supplies_kg = 3.0
        initial_supplies = self.agent.food_supplies_kg

        async def run_test():
            await self.behaviour.feed()
            self.assertEqual(self.agent.food_supplies_kg, 0.0)

        asyncio.run(run_test())

    def test_check_food_supplies_above_required(self):
        """Test check_food_supplies when supplies are above required"""
        self.agent.food_supplies_kg = 5.0
        self.agent.required_food_supplies_kg = 2.0

        async def run_test():
            await self.behaviour.check_food_supplies()
            self.assertFalse(self.agent.order_food_need)

        asyncio.run(run_test())

    def test_check_food_supplies_below_required(self):
        """Test check_food_supplies when supplies are below required"""
        self.agent.food_supplies_kg = 1.0
        self.agent.required_food_supplies_kg = 2.0

        async def run_test():
            await self.behaviour.check_food_supplies()
            self.assertTrue(self.agent.order_food_need)

        asyncio.run(run_test())

    def test_check_food_supplies_at_required(self):
        """Test check_food_supplies when supplies equal required"""
        self.agent.food_supplies_kg = 2.0
        self.agent.required_food_supplies_kg = 2.0

        async def run_test():
            await self.behaviour.check_food_supplies()
            self.assertFalse(self.agent.order_food_need)

        asyncio.run(run_test())

    def test_set_feeding_parameters_response_event_not_set(self):
        """Test set_feeding_parameters_response when event is not set"""
        self.agent.feeding_update_event.clear()

        async def run_test():
            await self.behaviour.set_feeding_parameters_response()
            # Should complete without error

        asyncio.run(run_test())

    def test_set_feeding_parameters_response_event_set(self):
        """Test set_feeding_parameters_response when event is set"""
        self.agent.feeding_update_event.set()

        async def run_test():
            await self.behaviour.set_feeding_parameters_response()
            # Event should be cleared after response
            self.assertFalse(self.agent.feeding_update_event.is_set())

        asyncio.run(run_test())

    def test_order_food(self):
        """Test order_food increases supplies"""
        initial_supplies = self.agent.food_supplies_kg
        order_amount = self.agent.order_amount_kg

        async def run_test():
            await self.behaviour.order_food()
            expected_supplies = initial_supplies + order_amount
            self.assertAlmostEqual(
                self.agent.food_supplies_kg, expected_supplies, places=2
            )
            self.assertFalse(self.agent.order_food_need)

        asyncio.run(run_test())


class TestFishCaretakerAgentIntegration(unittest.TestCase):
    """Integration tests for FishCaretakerAgent"""

    def test_multiple_fishermen_fish_data_registration(self):
        """Test registering fish data from multiple fishermen"""
        agent = FishCaretakerAgent("fish@localhost", "pass", "owner@localhost")

        fisher1_data = {"species": "salmon", "size": "large", "mass": 5.0, "time": ""}
        fisher2_data = {"species": "trout", "size": "small", "mass": 2.5, "time": ""}

        agent.fishes_taken["fisher1@localhost"] = [fisher1_data]
        agent.fishes_taken["fisher2@localhost"] = [fisher2_data]

        self.assertEqual(len(agent.fishes_taken), 2)
        self.assertEqual(len(agent.fishes_taken["fisher1@localhost"]), 1)
        self.assertEqual(len(agent.fishes_taken["fisher2@localhost"]), 1)

    def test_feeding_parameters_update(self):
        """Test updating feeding parameters"""
        agent = FishCaretakerAgent("fish@localhost", "pass", "owner@localhost")

        new_params = {"portion": 2.5, "interval_s": 5}
        agent.feeding_parameters = new_params

        self.assertEqual(agent.feeding_parameters["portion"], 2.5)
        self.assertEqual(agent.feeding_parameters["interval_s"], 5)

    def test_z_score_threshold_configuration(self):
        """Test configuring z-score threshold"""
        agent = FishCaretakerAgent("fish@localhost", "pass", "owner@localhost")
        agent.z_score_needs_restocking_alarm_point = 0.7

        self.assertEqual(agent.z_score_needs_restocking_alarm_point, 0.7)


if __name__ == "__main__":
    unittest.main()
