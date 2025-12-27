import json
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.template import Template
from .logger_config import get_logger

logger = get_logger("OwnerAgent")


class OwnerAgent(Agent):
    IF_CAN_ENTER_RESPONSE = "if_can_enter_response"
    IF_CAN_TAKE_FISH_RESPONSE = "if_can_take_fish_response"
    REGISTER_EXIT_RESPONSE = "register_exit_response"


    def __init__(self, jid, password, water_caretaker_jid):
        super().__init__(jid, password)

        self.water_caretaker_jid = water_caretaker_jid

        # Track active fishermen by JID to prevent double-counting
        self.active_fishermen = set()  # Set of JIDs currently in the fishery
        self.fisherman_limit = 10  # Maximum number of fishermen
        self.fishes_taken_count = 0
        self.fish_takes_limit = 50  # Daily limit for fish takes

    def check_if_entrance_possible(self, fisherman_jid):
        """
        Check if entrance is possible based on current fisherman count.
        Also checks if this fisherman is already in the fishery.
        
        Args:
            fisherman_jid: JID of the fisherman requesting entrance
            
        Returns:
            tuple: (allowed: bool, reason: str)
        """
        # Check if fisherman is already in the fishery
        if fisherman_jid in self.active_fishermen:
            return False, "You are already in the fishery."
        
        # Check if fishery is at capacity
        if len(self.active_fishermen) >= self.fisherman_limit:
            return False, f"Fishery is at capacity ({self.fisherman_limit} fishermen)."
        
        return True, "Entrance allowed."

    def check_if_can_take_fish(self):
        """Check if fisherman can take fish based on daily limit"""
        return self.fishes_taken_count < self.fish_takes_limit
    
    def get_fisherman_count(self):
        """Get current number of active fishermen"""
        return len(self.active_fishermen)

    class HandleIfCanEnterRequestBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=30)
            if msg:
                performative = msg.metadata.get("performative", "")
                protocol = msg.metadata.get("protocol", "")
                fisherman_jid = str(msg.sender)

                logger.info(f"Received entrance request from {fisherman_jid}: '{msg.body}'")

                allow, reason = self.agent.check_if_entrance_possible(fisherman_jid)

                reply = msg.make_reply()
                reply.metadata["protocol"] = OwnerAgent.IF_CAN_ENTER_RESPONSE

                if allow:
                    # Add fisherman to active set
                    self.agent.active_fishermen.add(fisherman_jid)
                    reply.body = "Yes, you can enter the fishery."
                    reply.metadata["performative"] = "agree"
                    logger.info(f"Sending entrance approval to {fisherman_jid}. Current fishermen: {self.agent.get_fisherman_count()}/{self.agent.fisherman_limit}")
                else:
                    reply.body = f"No, you can not enter the fishery. {reason}"
                    reply.metadata["performative"] = "refuse"
                    logger.warning(f"Sending entrance denial to {fisherman_jid}. Reason: {reason}. Current: {self.agent.get_fisherman_count()}/{self.agent.fisherman_limit}")

                await self.send(reply)

    class HandleIfCanTakeFishBehaviour(CyclicBehaviour):
        """Handle requests for permission to take fish (if_can_take_fish_request)"""

        async def run(self):
            msg = await self.receive(timeout=30)
            if msg:
                protocol = msg.metadata.get("protocol", "")
                try:
                    fish_data = json.loads(msg.body)
                    species = fish_data.get("species", "Unknown")
                    size = fish_data.get("size", "Unknown")
                    mass = fish_data.get("mass", 0)

                    logger.info(f"Received take fish permission request from {msg.sender}: {species} ({size}, {mass}kg)")

                    can_take = self.agent.check_if_can_take_fish()

                    reply = msg.make_reply()
                    reply.metadata["protocol"] = OwnerAgent.IF_CAN_TAKE_FISH_RESPONSE

                    if can_take:
                        reply.body = json.dumps(
                            {
                                "permission": "granted",
                                "message": "You can take this fish.",
                            }
                        )
                        reply.metadata["performative"] = "inform"
                        self.agent.fishes_taken_count += 1
                        logger.info(f"Permission granted. Fishes taken today: {self.agent.fishes_taken_count}/{self.agent.fish_takes_limit}")
                    else:
                        reply.body = json.dumps(
                            {
                                "permission": "denied",
                                "message": "Daily fish take limit exceeded.",
                            }
                        )
                        reply.metadata["performative"] = "disconfirm"
                        logger.warning(f"Permission denied. Daily limit reached: {self.agent.fishes_taken_count}/{self.agent.fish_takes_limit}")

                    await self.send(reply)
                except json.JSONDecodeError:
                    logger.error("Error parsing fish data from message")

    class HandleExitRegistrationBehaviour(CyclicBehaviour):
        """Handle exit registration from fishermen (register_exit_request)"""

        async def run(self):
            msg = await self.receive(timeout=30)
            if msg:
                protocol = msg.metadata.get("protocol", "")
                try:
                    exit_data = json.loads(msg.body)
                    fisherman = exit_data.get("fisherman", "Unknown")
                    fishes_taken = exit_data.get("fishes_taken", 0)
                    exit_time = exit_data.get("exit_time", "")

                    fisherman_jid = str(msg.sender)
                    logger.info(f"Received exit registration from {fisherman_jid}: fisherman={fisherman}, fishes_taken={fishes_taken}, exit_time={exit_time}")

                    # Remove fisherman from active set
                    if fisherman_jid in self.agent.active_fishermen:
                        self.agent.active_fishermen.remove(fisherman_jid)
                        logger.info(f"Removed {fisherman_jid} from active fishermen")
                    else:
                        logger.warning(f"Exit registration from {fisherman_jid} who was not in active fishermen list")

                    # Acknowledge exit
                    reply = msg.make_reply()
                    reply.metadata["protocol"] = OwnerAgent.REGISTER_EXIT_RESPONSE
                    reply.body = json.dumps(
                        {
                            "status": "acknowledged",
                            "message": "Exit registered successfully.",
                        }
                    )
                    reply.metadata["performative"] = "inform"

                    logger.info(f"Exit acknowledged. Current fishermen on fishery: {self.agent.get_fisherman_count()}/{self.agent.fisherman_limit}")

                    await self.send(reply)
                except json.JSONDecodeError:
                    logger.error("Error parsing exit data from message")

    class WaterAlarmHandleBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive()
            if msg:
                logger.warning(f"Water alarm received: [{msg.sender}] {msg.body}")

    async def setup(self):
        logger.info(f"Agent {self.jid} starting")

        self.setup_if_can_enter()
        self.setup_take_fish_permission()
        self.setup_exit_registration()
        self.setup_water_alarm()

    def setup_if_can_enter(self):
        from .fisher_agent import FisherAgent
        fisher_template = Template(
            to=self.jid,
            metadata={"protocol": FisherAgent.IF_CAN_ENTER_REQUEST},
        )

        handle_request_behaviour = self.HandleIfCanEnterRequestBehaviour()
        self.add_behaviour(handle_request_behaviour, fisher_template)

    def setup_take_fish_permission(self):
        """Setup handler for take fish permission requests"""
        from .fisher_agent import FisherAgent
        take_fish_template = Template(
            to=self.jid,
            metadata={"protocol": FisherAgent.IF_CAN_TAKE_FISH_REQUEST},
        )

        take_fish_behaviour = self.HandleIfCanTakeFishBehaviour()
        self.add_behaviour(take_fish_behaviour, take_fish_template)

    def setup_exit_registration(self):
        """Setup handler for exit registration"""
        from .fisher_agent import FisherAgent
        exit_template = Template(
            to=self.jid,
            metadata={"protocol": FisherAgent.REGISTER_EXIT_REQUEST},
        )

        exit_behaviour = self.HandleExitRegistrationBehaviour()
        self.add_behaviour(exit_behaviour, exit_template)

    def setup_water_alarm(self):
        water_alarm_template = Template(
            to=self.jid,
            sender=self.water_caretaker_jid,
            metadata={"protocol": "water-quality-alarm"},
        )
        water_alarm_behaviour = self.WaterAlarmHandleBehaviour()

        self.add_behaviour(water_alarm_behaviour, water_alarm_template)
