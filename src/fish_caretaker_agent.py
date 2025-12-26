import json
from spade.behaviour import CyclicBehaviour, PeriodicBehaviour
from spade.agent import Agent
from spade.template import Template
from .logger_config import get_logger

logger = get_logger("FishCaretakerAgent")


class FishCaretakerAgent(Agent):

    # ========== DEI ==========

    class MonitorFishState(CyclicBehaviour):
        async def run(self):
            pass

        async def collect_camera_data(self):
            pass

        async def collect_sonar_data(self):
            pass

    class ManageRestocking(CyclicBehaviour):
        async def run(self):
            pass

        async def if_needs_stocking(self):
            pass

        async def send_needs_stocking_alarm(self):
            pass

    class RegisterFishDataBehaviour(CyclicBehaviour):
        """Handle fish data registration from fishermen (register_fish_data_request)"""

        async def run(self):
            msg = await self.receive(timeout=30)
            if msg:
                protocol = msg.metadata.get("protocol", "")
                try:
                    fish_data = json.loads(msg.body)
                    species = fish_data.get("species", "Unknown")
                    size = fish_data.get("size", "Unknown")
                    mass = fish_data.get("mass", 0)
                    time = fish_data.get("time", "")

                    logger.info(f"[DEI] Received fish data registration from {msg.sender}: species={species}, size={size}, mass={mass}kg, action={action}, time={time}")

                    # Process fish data (update fish stock estimates, etc.)
                    # This is where you would update the fish stock database
                    # For now, just log it

                    # Send confirmation
                    reply = msg.make_reply()
                    reply.metadata["protocol"] = protocol
                    reply.body = json.dumps(
                        {
                            "status": "registered",
                            "message": "Fish data registered successfully.",
                        }
                    )
                    reply.metadata["performative"] = "agree"

                    logger.debug("[DEI] Fish data registration confirmed")

                    await self.send(reply)
                except json.JSONDecodeError:
                    logger.error("[DEI] Error parsing fish data from message")


    ##TODO - add to some behaviour vvvv
    async def set_diversity_target_response(self):
        pass

    # ========== FishHealthManager ==========

    class FishHealthManagerBehaviour(CyclicBehaviour):
        async def run(self):
            pass

        async def register_fish_size_response(self):
            pass

        async def calculate_fish_avg_size(self):
            pass

        async def revaluate_feeding(self):
            pass

        async def set_feeding_parameters_request(self):
            pass

    # ========== Feeder ==========

    class FeedingBehaviour(PeriodicBehaviour):
        async def run(self):
            pass

        async def set_feeding_parameters_response(self):
            pass

        def feed(self):
            pass

        async def check_food_supplies(self):
            pass

        async def order_food(self):
            print("[FISHCARETAKER][FEEDER] Food ordered (email sent)")

    async def setup(self):
        logger.info("Agent setup complete")

        await self.DEI_setup()
        await self.FishHealthManager_setup()
        await self.Feeder_setup()

    async def DEI_setup(self):
        # Monitor fish state
        self.add_behaviour(self.MonitorFishState())
        self.add_behaviour(self.ManageRestocking())

        # Register fish data handler
        fish_data_template = Template(metadata={"protocol": "register-fish-data"})
        register_fish_data_behaviour = self.RegisterFishDataBehaviour()
        self.add_behaviour(register_fish_data_behaviour, fish_data_template)

    async def FishHealthManager_setup(self):
        self.add_behaviour(self.FishHealthManagerBehaviour())


    async def Feeder_setup(self):
        feeding_behaviour = self.FeedingBehaviour(period=20)
        self.add_behaviour(feeding_behaviour)
