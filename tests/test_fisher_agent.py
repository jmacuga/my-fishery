import unittest
import asyncio
from unittest.mock import AsyncMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.fisher_agent import FisherAgent


class TestFisherAgentBasic(unittest.TestCase):
    def test_register_enter_sets_on_fishery(self):
        """register_enter should set agent.is_on_fishery to True"""
        behaviour = FisherAgent.HandleIfCanEnterResponseBehaviour()

        class DummyAgent:
            pass

        dummy = DummyAgent()
        dummy.is_on_fishery = False
        behaviour.agent = dummy

        behaviour.register_enter()

        self.assertTrue(dummy.is_on_fishery)

    def test_register_take_fish_appends(self):
        """register_take_fish should append fish record to agent.fishes_caught"""
        behaviour = FisherAgent.HandleTakeFishResponseBehaviour()

        class DummyAgent:
            pass

        dummy = DummyAgent()
        dummy.fishes_caught = []
        behaviour.agent = dummy

        fish_data = {"species": "Carp", "size": "M", "mass": 1.5}

        behaviour.register_take_fish(fish_data)

        self.assertEqual(len(dummy.fishes_caught), 1)
        recorded = dummy.fishes_caught[0]
        self.assertEqual(recorded["species"], "Carp")
        self.assertEqual(recorded["size"], "M")
        self.assertAlmostEqual(recorded["mass"], 1.5)


class TestUserInputBehaviourAsync(unittest.TestCase):
    def setUp(self):
        self.behaviour = FisherAgent.UserInputBehaviour()

        class DummyAgent:
            def __init__(self):
                self.jid = "fisher@localhost"

        self.agent = DummyAgent()
        self.agent.owner_jid = "owner@localhost"
        self.agent.fish_caretaker_jid = None
        self.agent.fishes_caught = []
        self.behaviour.agent = self.agent

    def test_request_enter_fishery_sends(self):
        """request_enter_fishery should set pending flag and call send"""
        self.behaviour.send = AsyncMock()

        async def run_test():
            await self.behaviour.request_enter_fishery()

        asyncio.run(run_test())

        self.assertTrue(hasattr(self.agent, "pending_entrance_request"))
        self.assertTrue(self.agent.pending_entrance_request)
        self.behaviour.send.assert_awaited()

    def test_request_take_fish_permission_sends_and_sets_pending(self):
        """request_take_fish_permission should set pending_take_fish_request and call send"""
        self.behaviour.send = AsyncMock()

        async def run_test():
            await self.behaviour.request_take_fish_permission("Carp", "M", 1.5)

        asyncio.run(run_test())

        self.assertIn("pending_take_fish_request", self.agent.__dict__)
        pending = self.agent.pending_take_fish_request
        self.assertEqual(pending["species"], "Carp")
        self.behaviour.send.assert_awaited()

    def test_register_fish_data_skips_when_no_caretaker(self):
        """register_fish_data should return early if no fish_caretaker_jid configured"""
        # fish_caretaker_jid is None in setUp
        self.behaviour.send = AsyncMock()

        async def run_test():
            await self.behaviour.register_fish_data("Carp", "M", 1.5)

        asyncio.run(run_test())

        # Since no fish_caretaker_jid, send should not be awaited
        self.behaviour.send.assert_not_awaited()

    def test_register_exit_sets_pending_and_sends(self):
        """register_exit should set pending_exit_registration and call send"""
        self.behaviour.send = AsyncMock()
        self.agent.fishes_caught = [{"species": "Carp", "mass": 1.5}]

        async def run_test():
            await self.behaviour.register_exit()

        asyncio.run(run_test())

        self.assertTrue(self.agent.pending_exit_registration)
        self.behaviour.send.assert_awaited()


if __name__ == "__main__":
    unittest.main()
