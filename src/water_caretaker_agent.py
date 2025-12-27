import asyncio
import math

from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour
from spade.message import Message

from random import normalvariate
from .logger_config import get_logger
from .misc import get_random_data, calculate_z_score

logger = get_logger("WaterCaretakerAgent")

class WaterCaretakerAgent(Agent):
    def __init__(self, jid, password, owner_jid, logs_out=True):
        super().__init__(jid, password)

        self.owner_jid = owner_jid
        self.logs_out = logs_out

        self.ph_data = []

        self.last_values = 10
        self.z_score_alert = 1.1

    class WaterQualityMeasureBehaviour(PeriodicBehaviour):
        async def run(self):
            await self.collect_data()

        def aeration(self):
            logger.info("Aeration started (pump ON)")

        async def send_water_quality_alarm(self, z_score):
            logger.warning(f"ALERT: Unusual pH change! z_score: {z_score}")

            msg = Message(
                to=self.agent.owner_jid,
                body=f"Water quality alarm, z_score value: {z_score}",
                metadata={"performative": "alarm", "protocol": "water-quality-alarm"},
            )
            await self.send(msg)

            self.aeration()

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
