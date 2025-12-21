from spade.behaviour import CyclicBehaviour, PeriodicBehaviour
from spade.agent import Agent
from spade.template import Template


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

    ##TODO - add to some behaviour vvvv
    async def set_diversity_target_response(self):
        pass

    async def register_fish_data_response(self):
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
        print(f"[{self.__class__.__name__}] setup")

        self.DEI_setup()
        self.FishHealthManager_setup()
        self.Feeder_setup()

    async def DEI_setup(self):
        dei_template = Template(metadata={"protocol": "register-fish-data"})
        self.add_behaviour(self.MonitorFishState(), dei_template)
        self.add_behaviour(self.ManageRestocking(), dei_template)

    async def FishHealthManager_setup(self):
        size_template = Template(metadata={"protocol": "register-fish-size"})
        self.add_behaviour(self.FishHealthManagerBehaviour(), size_template)

    async def Feeder_setup(self):
        feeding_behaviour = self.FeedingBehaviour(period=20)
        self.add_behaviour(feeding_behaviour)
