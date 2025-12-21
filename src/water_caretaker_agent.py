import spade
from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour


class WaterCaretakerAgent(Agent):
    class WaterQualityMeasureBehaviour(PeriodicBehaviour):
        async def run(self):
            pass

        def calculate_quality(self):
            return 0

        async def aeration(self):
            print(f"[{self.__class__.__name__}] Aeration started (pump ON)")

        async def collect_data(self):
            pass

        async def send_water_quality_alarm(self):
            pass

    async def setup(self):
        print(f"[{self.__class__.__name__}] setup")
        b = self.WaterQualityMeasureBehaviour()
        self.add_behaviour(b)
