import asyncio
import json
from uuid import uuid4 as uuid
from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour
from spade.message import Message
from .logger_config import get_logger
from .misc import get_random_data, calculate_z_score
from .protocols import Protocols

logger = get_logger("WaterCaretakerAgent")


class WaterCaretakerAgent(Agent):
    def __init__(self, jid, password, owner_jid):
        super().__init__(jid, password)

        self.owner_jid = owner_jid
        self.ph_data = []

        self.last_values = 10
        self.z_score_alert = 1.1

    class WaterQualityMeasureBehaviour(PeriodicBehaviour):
        async def run(self):
            await self.collect_data()

        async def aeration(self):
            logger.info("Aeration started (pump ON)")
            await asyncio.sleep(5)
            logger.info("Aeration ended (pump OFF)")

        async def send_water_quality_alarm(self, z_score):
            logger.warning(f"ALERT: Unusual pH change! z_score: {z_score}")
            payload = {"z_score": z_score, "ph_data": self.agent.ph_data}
            try:
                msg = Message(
                    to=self.agent.owner_jid,
                    body=json.dumps(payload),
                    metadata={
                        "performative": "request",
                        "protocol": Protocols.SEND_WATER_QUALITY_ALARM.value,
                        "language": "JSON",
                        "reply-with": str(uuid()),
                        "conversation-id": str(uuid()),
                        "in-reply-to": str(uuid()),
                    },
                )
                await self.send(msg)
                await self.aeration()
            except json.JSONDecodeError as e:
                logger.error(f"JSONDecodeError while sending quality alarm: {e}")

        async def collect_data(self):
            ph_data = get_random_data(10, 5)
            logger.debug(f"Collected pH data: {ph_data}")

            self.agent.ph_data.append(ph_data)
            await self.calculate_quality()

            await asyncio.sleep(1)

        async def calculate_quality(self):
            z_score = calculate_z_score(self.agent.ph_data, self.agent.last_values)
            if z_score is not None and abs(z_score) > self.agent.z_score_alert:
                await self.send_water_quality_alarm(z_score)

    async def setup(self):
        logger.info("Agent setup complete")
        b = self.WaterQualityMeasureBehaviour(period=2)
        self.add_behaviour(b)
