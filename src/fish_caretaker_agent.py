import json, asyncio
from spade.behaviour import CyclicBehaviour, PeriodicBehaviour
from spade.agent import Agent
from spade.template import Template
from spade.message import Message
from .logger_config import get_logger

from .misc import get_random_data, calculate_z_score

logger = get_logger("FishCaretakerAgent")


class FishCaretakerAgent(Agent):
    REGISTER_FISH_DATA_RESPONSE = "response_fish_data_response"
    SEND_NEEDS_STOCKING_ALARM = "send_needs_stocking_alarm"

    def __init__(self, jid, password, owner_jid):
        super().__init__(jid, password)
        self.camera_data = []
        self.sonar_data = []
        self.fishes_taken = {}
        self.z_score_needs_restocking_alarm_point = 0.5
        self.owner_jid = owner_jid

    # ========== DEI ==========

    class MonitorFishState(CyclicBehaviour):
        async def run(self):
            self.agent.camera_data.append(self.collect_camera_data())
            self.agent.sonar_data.append(self.collect_sonar_data())
            await asyncio.sleep(1)

        def collect_camera_data(self):
            return max(0, get_random_data(20, 5))

        def collect_sonar_data(self):
            return max(0, get_random_data(20, 5))

    class ManageRestocking(CyclicBehaviour):
        async def run(self):
            needs_stocking, z_score = self.if_needs_stocking()
            if needs_stocking:
                await self.send_needs_stocking_alarm(z_score)
            await asyncio.sleep(1)

        def if_needs_stocking(self):
            camera_z_score = calculate_z_score(self.agent.camera_data)
            sonar_z_score = calculate_z_score(self.agent.sonar_data)
            if camera_z_score is not None and sonar_z_score is not None:
                index = max(abs(camera_z_score), abs(sonar_z_score))
                return (index < self.agent.z_score_needs_restocking_alarm_point), index
            return False, None
                
        async def send_needs_stocking_alarm(self, z_score):
            logger.warning(f"ALERT: Not enough fish! z_score: {z_score}")

            msg = Message(
                to=self.agent.owner_jid,
                body=f"Not enough fish, z_score value: {z_score}",
                metadata={"performative": "alarm", "protocol": FishCaretakerAgent.SEND_NEEDS_STOCKING_ALARM}
            )
            await self.send(msg)


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

                    logger.info(f"[DEI] Received fish data registration from {msg.sender}: species={species}, size={size}, mass={mass}kg, time={time}")

                    # Process fish data (update fish stock estimates, etc.)
                    # This is where you would update the fish stock database
                    # For now, just log it

                    # Register data in dict
                    if msg.sender not in self.agent.fishes_taken.keys():
                        self.agent.fishes_taken[msg.sender] = []
                    self.agent.fishes_taken[msg.sender].append(fish_data)

                    logger.info(f"Currently taken fishes: {self.agent.fishes_taken}")

                    # Send confirmation
                    reply = msg.make_reply()
                    reply.metadata["protocol"] = FishCaretakerAgent.REGISTER_FISH_DATA_RESPONSE
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
        from .fisher_agent import FisherAgent
        # Monitor fish state
        self.add_behaviour(self.MonitorFishState())

        # Check if needs restocking and raise an alarm
        self.add_behaviour(self.ManageRestocking())

        # Register fish data handler
        fish_data_template = Template(metadata={"protocol": FisherAgent.REGISTER_FISH_DATA_REQUEST})
        register_fish_data_behaviour = self.RegisterFishDataBehaviour()
        self.add_behaviour(register_fish_data_behaviour, fish_data_template)

    async def FishHealthManager_setup(self):
        self.add_behaviour(self.FishHealthManagerBehaviour())


    async def Feeder_setup(self):
        feeding_behaviour = self.FeedingBehaviour(period=20)
        self.add_behaviour(feeding_behaviour)
