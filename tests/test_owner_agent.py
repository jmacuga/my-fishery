import unittest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
import sys

# allow importing from src
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.owner_agent import OwnerAgent
from src.protocols import Protocols


class TestOwnerAgentInit(unittest.TestCase):
    def test_initial_state(self):
        agent = OwnerAgent("owner@localhost", "pw", "water@localhost", "fish@localhost")
        self.assertEqual(agent.water_caretaker_jid, "water@localhost")
        self.assertEqual(agent.fish_caretaker_jid, "fish@localhost")
        self.assertIsInstance(agent.active_fishermen, set)
        self.assertEqual(agent.fisherman_limit, 10)
        self.assertEqual(agent.fishes_taken_count, 0)
        self.assertEqual(agent.fish_takes_limit, 50)
        self.assertFalse(agent.pending_stocking_prompt.is_set())
        self.assertIsNone(agent.last_stocking_alarm)


class TestOwnerAgentLogic(unittest.TestCase):
    def setUp(self):
        self.agent = OwnerAgent(
            "owner@localhost", "pw", "water@localhost", "fish@localhost"
        )

    def test_check_if_entrance_possible_allowed(self):
        allowed, reason = self.agent.check_if_entrance_possible("fisher1@localhost")
        self.assertTrue(allowed)
        self.assertEqual(reason, "Entrance allowed.")

    def test_check_if_entrance_possible_already_inside(self):
        self.agent.active_fishermen.add("fisher1@localhost")
        allowed, reason = self.agent.check_if_entrance_possible("fisher1@localhost")
        self.assertFalse(allowed)
        self.assertIn("already in the fishery", reason)

    def test_check_if_entrance_possible_at_capacity(self):
        # fill up active_fishermen to limit
        for i in range(self.agent.fisherman_limit):
            self.agent.active_fishermen.add(f"fisher{i}@localhost")
        allowed, reason = self.agent.check_if_entrance_possible("newfisher@localhost")
        self.assertFalse(allowed)
        self.assertIn("at capacity", reason)

    def test_check_if_can_take_fish(self):
        self.agent.fishes_taken_count = 0
        self.agent.fish_takes_limit = 2
        self.assertTrue(self.agent.check_if_can_take_fish())
        self.agent.fishes_taken_count = 2
        self.assertFalse(self.agent.check_if_can_take_fish())

    def test_get_fisherman_count(self):
        self.agent.active_fishermen.update({"a@x", "b@x"})
        self.assertEqual(self.agent.get_fisherman_count(), 2)


class TestBehaviours(unittest.TestCase):
    def setUp(self):
        self.agent = OwnerAgent(
            "owner@localhost", "pw", "water@localhost", "fish@localhost"
        )

    @patch.object(
        OwnerAgent.HandleIfCanEnterRequestBehaviour, "receive", new_callable=AsyncMock
    )
    def test_handle_if_can_enter_request_allow(self, mock_receive):
        behaviour = self.agent.HandleIfCanEnterRequestBehaviour()
        behaviour.agent = self.agent

        # fake incoming message
        msg = Mock()
        msg.sender = "fisher1@localhost"
        msg.metadata = {"conversation-id": "c1", "reply-with": "r1"}
        msg.body = "request"
        reply = Mock(metadata={}, body="")
        msg.make_reply = Mock(return_value=reply)

        mock_receive.return_value = msg

        # patch send so it doesn't try network
        behaviour.send = AsyncMock()

        asyncio.run(behaviour.run())

        # fisherman should be added
        self.assertIn("fisher1@localhost", self.agent.active_fishermen)
        # reply object should have protocol set
        self.assertEqual(
            reply.metadata.get("protocol"), Protocols.IF_CAN_ENTER_RESPONSE.value
        )
        self.assertEqual(reply.metadata.get("performative"), "agree")

    @patch.object(
        OwnerAgent.HandleIfCanEnterRequestBehaviour, "receive", new_callable=AsyncMock
    )
    def test_handle_if_can_enter_request_refuse(self, mock_receive):
        behaviour = self.agent.HandleIfCanEnterRequestBehaviour()
        behaviour.agent = self.agent

        # fill capacity
        for i in range(self.agent.fisherman_limit):
            self.agent.active_fishermen.add(f"f{i}@localhost")

        msg = Mock()
        msg.sender = "newfisher@localhost"
        msg.metadata = {"conversation-id": "c2", "reply-with": "r2"}
        msg.body = "request"
        reply = Mock(metadata={}, body="")
        msg.make_reply = Mock(return_value=reply)

        mock_receive.return_value = msg
        behaviour.send = AsyncMock()

        asyncio.run(behaviour.run())

        self.assertEqual(reply.metadata.get("performative"), "refuse")
        self.assertIn(
            "at capacity", json.loads(reply.body)["reason"]
        )  # body contains reason

    @patch.object(
        OwnerAgent.HandleIfCanTakeFishBehaviour, "receive", new_callable=AsyncMock
    )
    def test_handle_if_can_take_fish_allow(self, mock_receive):
        behaviour = self.agent.HandleIfCanTakeFishBehaviour()
        behaviour.agent = self.agent

        fish_data = {"species": "salmon", "size": "L", "mass": 3}
        msg = Mock()
        msg.sender = "fisher1@localhost"
        msg.metadata = {"conversation-id": "c3", "reply-with": "r3"}
        msg.body = json.dumps(fish_data)
        reply = Mock(metadata={}, body="")
        msg.make_reply = Mock(return_value=reply)

        mock_receive.return_value = msg
        behaviour.send = AsyncMock()

        # ensure under limit
        self.agent.fishes_taken_count = 0
        self.agent.fish_takes_limit = 2

        asyncio.run(behaviour.run())

        self.assertEqual(reply.metadata.get("performative"), "agree")
        self.assertEqual(self.agent.fishes_taken_count, 1)

    @patch.object(
        OwnerAgent.HandleIfCanTakeFishBehaviour, "receive", new_callable=AsyncMock
    )
    def test_handle_if_can_take_fish_refuse(self, mock_receive):
        behaviour = self.agent.HandleIfCanTakeFishBehaviour()
        behaviour.agent = self.agent

        fish_data = {"species": "salmon", "size": "L", "mass": 3}
        msg = Mock()
        msg.sender = "fisher1@localhost"
        msg.metadata = {"conversation-id": "c4", "reply-with": "r4"}
        msg.body = json.dumps(fish_data)
        reply = Mock(metadata={}, body="")
        msg.make_reply = Mock(return_value=reply)

        mock_receive.return_value = msg
        behaviour.send = AsyncMock()

        # set at limit
        self.agent.fishes_taken_count = 5
        self.agent.fish_takes_limit = 5

        asyncio.run(behaviour.run())

        self.assertEqual(reply.metadata.get("performative"), "refuse")
        self.assertEqual(self.agent.fishes_taken_count, 5)

    @patch.object(
        OwnerAgent.HandleExitRegistrationBehaviour, "receive", new_callable=AsyncMock
    )
    def test_handle_exit_registration_when_present(self, mock_receive):
        behaviour = self.agent.HandleExitRegistrationBehaviour()
        behaviour.agent = self.agent

        self.agent.active_fishermen.add("fisher_exit@localhost")

        exit_data = {
            "fisherman": "fisher_exit@localhost",
            "fishes_taken": 1,
            "exit_time": "now",
        }
        msg = Mock()
        msg.sender = "fisher_exit@localhost"
        msg.metadata = {"conversation-id": "c5", "reply-with": "r5"}
        msg.body = json.dumps(exit_data)
        reply = Mock(metadata={}, body="")
        msg.make_reply = Mock(return_value=reply)

        mock_receive.return_value = msg
        behaviour.send = AsyncMock()

        asyncio.run(behaviour.run())

        self.assertNotIn("fisher_exit@localhost", self.agent.active_fishermen)
        self.assertEqual(reply.metadata.get("performative"), "inform")
        self.assertIn("acknowledged", json.loads(reply.body)["status"])

    @patch.object(
        OwnerAgent.ReceiveNeedsStockingAlarmBehaviour, "receive", new_callable=AsyncMock
    )
    def test_receive_needs_stocking_parses_json(self, mock_receive):
        behaviour = self.agent.ReceiveNeedsStockingAlarmBehaviour()
        behaviour.agent = self.agent

        payload = {"z_score": "0.3", "message": "Not enough fish"}
        msg = Mock()
        msg.body = json.dumps(payload)
        msg.sender = "fish@localhost"

        mock_receive.return_value = msg

        # pending_stocking_prompt should be an Event
        self.agent.pending_stocking_prompt.clear()

        asyncio.run(behaviour.run())

        self.assertTrue(self.agent.pending_stocking_prompt.is_set())
        self.assertEqual(self.agent.last_stocking_alarm, payload)


if __name__ == "__main__":
    unittest.main()
