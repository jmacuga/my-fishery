import json, asyncio
from uuid import uuid4 as uuid
from typing import Optional
from spade.behaviour import CyclicBehaviour, PeriodicBehaviour
from spade.agent import Agent
from spade.template import Template
from spade.message import Message
from .logger_config import get_logger

from .misc import get_random_data, calculate_z_score
from .protocols import Protocols

logger = get_logger("FishCaretakerAgent")


class FishCaretakerAgent(Agent):

    def __init__(self, jid, password, owner_jid):
        super().__init__(jid, password)
        self.camera_data = []
        self.sonar_data = []
        self.fishes_taken = {}
        self.z_score_needs_restocking_alarm_point = 0.5
        self.owner_jid = owner_jid

        self.feeding_parameters = {"portion": 1, "interval_s": 2}

        self.feeding_update_event = asyncio.Event()

        self.food_supplies_kg = 10.0
        self.required_food_supplies_kg = 2.0
        self.order_food_need = False
        self.order_amount_kg = 25.0

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

        def if_needs_stocking(self) -> tuple[bool, Optional[float]]:
            camera_z_score: Optional[float] = calculate_z_score(self.agent.camera_data)
            sonar_z_score: Optional[float] = calculate_z_score(self.agent.sonar_data)

            if camera_z_score is not None and sonar_z_score is not None:
                camera_z_score = round(float(camera_z_score), 2)
                sonar_z_score = round(float(sonar_z_score), 2)
                index = max(abs(camera_z_score), abs(sonar_z_score))
                return (
                    (index < self.agent.z_score_needs_restocking_alarm_point),
                    index,
                )

            return False, None

        async def send_needs_stocking_alarm(self, z_score: Optional[float]):
            logger.warning(f"ALERT: Not enough fish! z_score: {z_score}")
            payload = {
                "z_score": f"{z_score if z_score else 'N/A'}",
                "message": "Not enough fish - fishery needs stocking",
            }
            try:
                msg = Message(
                    to=self.agent.owner_jid,
                    body=json.dumps(payload),
                    metadata={
                        "performative": "request",
                        "protocol": Protocols.SEND_NEEDS_STOCKING_ALARM.value,
                        "language": "JSON",
                        "reply-with": str(uuid()),
                        "conversation-id": str(uuid()),
                    },
                )
                await self.send(msg)
            except json.JSONDecodeError as e:
                logger.error(
                    f"Exception while sending nedds stocking alarm. Reason: {e}"
                )

    class RegisterFishDataBehaviour(CyclicBehaviour):
        """Handle fish data registration from fishermen (register_fish_data_request)"""

        async def run(self):
            msg = await self.receive(timeout=30)
            if msg:
                try:
                    conversation_id = msg.metadata.get("conversation-id")
                    in_reply_to = msg.metadata.get("reply-with")
                    fish_data = json.loads(msg.body)
                    species = fish_data.get("species", "Unknown")
                    size = fish_data.get("size", "Unknown")
                    mass = fish_data.get("mass", 0)
                    time = fish_data.get("time", "")

                    logger.info(
                        f"[DEI] Received fish data registration from {msg.sender}: species={species}, size={size}, mass={mass}kg, time={time}"
                    )

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
                    reply.metadata["protocol"] = (
                        Protocols.REGISTER_FISH_DATA_RESPONSE.value
                    )
                    reply.body = json.dumps(
                        {
                            "status": "registered",
                            "message": "Fish data registered successfully.",
                        }
                    )
                    reply.metadata["performative"] = "agree"
                    reply.metadata["language"] = "JSON"
                    reply.metadata["reply-with"] = str(uuid())
                    reply.metadata["in-reply-to"] = in_reply_to
                    reply.metadata["conversation-id"] = conversation_id

                    logger.debug("[DEI] Fish data registration confirmed")

                    await self.send(reply)
                except json.JSONDecodeError:
                    logger.error("[DEI] Error parsing fish data from message")

    ##TODO - add to some behaviour vvvv
    async def set_diversity_target_response(self):
        pass

    # ========== FishHealthManager ==========

    # class FishHealthManagerBehaviour(CyclicBehaviour):
    #     async def run(self):
    #         # await self.revaluate_feeding()
    #         await asyncio.sleep(5)

    #     # async def revaluate_feeding(self):
    #     #     """Calculate current feeding parameters based on fish data"""
    #     #     if self.check_fish_state():
    #     #         await self.set_feeding_parameters_request({"portion": 0.0, "interval_s": 0})

    #     # async def set_feeding_parameters_request(self, feeding_parameters):
    #     #     """Request for Feeder to change feeding parameters"""
    #     #     logger.info("[FishHealthManager] New feeding parameters acknowledged")
    #     #     self.agent.feeding_parameters = feeding_parameters
    #     #     self.agent.feeding_update_event.set()

    #     async def set_feeding_parameters_request(self, feeding_parameters):
    #         """Request for Feeder to change feeding parameters (protocol message)."""
    #         msg = Message(
    #             to=str(self.agent.jid),
    #             body=json.dumps(feeding_parameters),
    #             metadata={
    #                 "performative": "request",
    #                 "protocol": FishCaretakerAgent.SET_FEEDING_PARAMETERS_REQUEST,
    #             },
    #         )
    #         logger.info(f"[FishHealthManager] Sending set_feeding_parameters_request: {feeding_parameters}")
    #         await self.send(msg)

    #     # def check_fish_state(self):
    #     #     return sum(self.agent.camera_data)/len(self.agent.camera_data) > 10 and sum(self.agent.sonar_data)/len(self.agent.sonar_data) > 10


    # ========== Feeder ==========

    # class FeedingBehaviour(PeriodicBehaviour):
    #     async def run(self):
    #         await self.set_feeding_parameters_response()

    #     async def set_feeding_parameters_response(self):
    #         if self.agent.feeding_update_event.is_set():
    #             logger.info("[Feeder] New feeding parameters acknowledged")
    #             self.agent.feeding_update_event.clear()

    #     def feed(self):
    #         pass

    #     async def check_food_supplies(self):
    #         pass

    #     async def order_food(self):
    #         print("[FISHCARETAKER][FEEDER] Food ordered (email sent)")

    # ========== Feeder ==========

    # class HandleSetFeedingParametersRequestBehaviour(CyclicBehaviour):
    #     """Handle set_feeding_parameters_request and reply with agree (set_feeding_parameters_response)."""

    #     async def run(self):
    #         msg = await self.receive(timeout=30)

    #         # obsluzenie błędów
    #         if not msg:
    #             return

    #         if msg.metadata.get("protocol") != FishCaretakerAgent.SET_FEEDING_PARAMETERS_REQUEST:
    #             return

    #         try:
    #             new_params = json.loads(msg.body)
    #         except json.JSONDecodeError:
    #             logger.error("[Feeder] Invalid JSON in set_feeding_parameters_request")
    #             return

    #         # Minimalna walidacja
    #         portion = float(new_params.get("portion", self.agent.feeding_parameters["portion"]))
    #         interval_s = int(new_params.get("interval_s", self.agent.feeding_parameters["interval_s"]))

    #         # zabezpieczenie zeby nie wywolywac caly czas przy ustawieniu na 0
    #         interval_s = max(1, interval_s)
    #         self.agent.feeding_parameters = {"portion": portion, "interval_s": interval_s}
    #         self.agent.feeding_update_event.set()

    #         logger.info(f"[Feeder] Updated feeding parameters to: {self.agent.feeding_parameters}")

    #         # Odpowiedź "agree"
    #         reply = msg.make_reply()
    #         reply.metadata["protocol"] = FishCaretakerAgent.SET_FEEDING_PARAMETERS_RESPONSE
    #         reply.metadata["performative"] = "agree"
    #         reply.body = json.dumps(
    #             {
    #                 "status": "ok",
    #                 "feeding_parameters": self.agent.feeding_parameters,
    #             }
    #         )
    #         await self.send(reply)


    class FeedingBehaviour(PeriodicBehaviour):
        """
        Realizuje obowiązki Feedera:
        - set_feeding_parameters_response (obsługiwane przez handler wyżej + event)
        - feed
        - check_food_supplies (+ ewentualnie order_food)
        """

        async def run(self):
            # 1) jeśli były zmiany parametrów – „ack” lokalny (log + clear event)
            await self.set_feeding_parameters_response()

            # 2) karmienie
            await self.feed()

            # 3) sprawdzenie magazynu i ewentualne zamówienie
            await self.check_food_supplies()
            if self.agent.order_food_need:
                await self.order_food()

        async def set_feeding_parameters_response(self):
            if self.agent.feeding_update_event.is_set():
                logger.info(f"[Feeder] set_feeding_parameters_response: {self.agent.feeding_parameters}")
                self.agent.feeding_update_event.clear()

        async def feed(self):
            portion = float(self.agent.feeding_parameters.get("portion", 0.0))
            if portion <= 0:
                logger.debug("[Feeder] Portion <= 0, skipping feeding.")
                return

            if self.agent.food_supplies_kg <= 0:
                logger.warning("[Feeder] No food in storage! Feeding skipped.")
                return

            eaten = min(portion, self.agent.food_supplies_kg)
            self.agent.food_supplies_kg -= eaten
            logger.info(f"[Feeder] Feeding done: {eaten:.2f} kg. Supplies left: {self.agent.food_supplies_kg:.2f} kg")

        async def check_food_supplies(self):
            """git
            Bezpieczeństwo roli:
            food_supplies < required_food_supplies => order_food_need = true
            """
            # prosta heurystyka: required = minimalny próg (możesz też liczyć z harmonogramu)
            required = float(self.agent.required_food_supplies_kg)
            self.agent.order_food_need = self.agent.food_supplies_kg < required

            logger.debug(
                f"[Feeder] check_food_supplies: supplies={self.agent.food_supplies_kg:.2f} kg, "
                f"required={required:.2f} kg, order_food_need={self.agent.order_food_need}"
            )

        async def order_food(self):
            """
            Zamawianie karmy (symulacja).
            """
            logger.warning("[Feeder] Low stock -> ordering food... (simulation: email sent)")
            # symulacja czasu zamówienia/dostawy
            await asyncio.sleep(1)

            self.agent.food_supplies_kg += float(self.agent.order_amount_kg)
            self.agent.order_food_need = False

            logger.info(f"[Feeder] Food delivered: +{self.agent.order_amount_kg:.2f} kg. Supplies now: {self.agent.food_supplies_kg:.2f} kg")


    # ========== Setup ==========

    async def setup(self):
        logger.info("Agent setup complete")

        await self.DEI_setup()
        # await self.FishHealthManager_setup()
        await self.Feeder_setup()

    async def DEI_setup(self):

        # Monitor fish state
        self.add_behaviour(self.MonitorFishState())

        # Check if needs restocking and raise an alarm
        self.add_behaviour(self.ManageRestocking())

        # Register fish data handler
        fish_data_template = Template(
            metadata={
                "protocol": Protocols.REGISTER_FISH_DATA_REQUEST.value,
                "performative": "request",
                "language": "JSON",
            }
        )
        register_fish_data_behaviour = self.RegisterFishDataBehaviour()
        self.add_behaviour(register_fish_data_behaviour, fish_data_template)

    # async def FishHealthManager_setup(self):
    #     fish_health_manager_behaviour = self.FishHealthManagerBehaviour()

    #     self.add_behaviour(fish_health_manager_behaviour)

    # async def Feeder_setup(self):
    #     feeding_behaviour = self.FeedingBehaviour(period=20)
    #     self.add_behaviour(feeding_behaviour)

    async def Feeder_setup(self):
        # Handler request -> response (set_feeding_parameters_request/response)
        # feeder_req_template = Template(metadata={"protocol": FishCaretakerAgent.SET_FEEDING_PARAMETERS_REQUEST})
        # self.add_behaviour(self.HandleSetFeedingParametersRequestBehaviour(), feeder_req_template)

        # Karmienie cykliczne – okres bierzemy z parametrów (startowo 20s)
        feeding_behaviour = self.FeedingBehaviour(period=int(self.feeding_parameters.get("interval_s", 20)))

        self.add_behaviour(feeding_behaviour)
