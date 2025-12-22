from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.template import Template


class OwnerAgent(Agent):
    def __init__(self, jid, password, fisher_jid, water_caretaker_jid):
        super().__init__(jid, password)

        self.fisher_jid = fisher_jid
        self.water_caretaker_jid = water_caretaker_jid

        self.fishermans_number = 0

    class HandleRequestsBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=30)  # czekamy na request
            if msg:
                performative = msg.metadata.get("performative", "")
                protocol = msg.metadata.get("protocol", "")

                print(
                    f"[{self.agent.__class__.__name__}] Received message {msg.sender}: '{msg.body}' "
                )

                allow = check_if_entrance_possible

                reply = msg.make_reply()
                reply.metadata["protocol"] = protocol

                if allow:
                    reply.body = "Yes, you can enter the fishery."
                    reply.metadata["performative"] = "agree"
                    print(
                        f"[{self.agent.__class__.__name__}] Sending entrance aproval."
                    )

                    self.agent.fishermans_number += 1
                else:
                    reply.body = "No, you can not enter the fishery."
                    reply.metadata["performative"] = "refuse"
                    print(f"[{self.agent.__class__.__name__}] Sending entrance denial.")

                await self.send(reply)

            else:
                print(f"[{self.agent.__class__.__name__}] No new fishermans...")

            def check_if_entrance_possible(self):  # TODO check fishers num
                return True

    class HandleRequestsBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=30)
            if msg:
                print(
                    f"[{self.agent.__class__.__name__}] Received message {msg.sender}: '{msg.body}' "
                )

                allow = True  # TODO check fishers num

                reply = msg.make_reply()
                reply.metadata["protocol"] = msg.metadata.get("protocol", "")

                if allow:
                    reply.body = "Yes, you can enter the fishery."
                    reply.metadata["performative"] = "agree"
                    print(
                        f"[{self.agent.__class__.__name__}] Sending entrance aproval."
                    )
                else:
                    reply.body = "No, you can not enter the fishery."
                    reply.metadata["performative"] = "refuse"
                    print(f"[{self.agent.__class__.__name__}] Sending entrance denial.")

                await self.send(reply)

    class WaterAlarmHandleBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive()
            if msg:
                print(
                    f"[{self.agent.__class__.__name__}] Water alarm received: [{msg.sender}] {msg.body}"
                )

    async def setup(self):
        print(f"[{self.__class__.__name__}] Agent {self.jid} startuje.")

        self.setup_fisher_access()
        self.setup_water_alarm()

    def setup_fisher_access(self):
        fisher_template = Template(
            to=self.jid,
            sender=self.fisher_jid,
            metadata={"protocol": "fishing-access"},
        )

        handle_request_behaviour = self.HandleRequestsBehaviour()

        self.add_behaviour(handle_request_behaviour, fisher_template)

    def setup_water_alarm(self):
        water_alarm_template = Template(
            to=self.jid,
            sender=self.water_caretaker_jid,
            metadata={"protocol": "water-quality-alarm"},
        )
        water_alarm_behaviour = self.WaterAlarmHandleBehaviour()

        self.add_behaviour(water_alarm_behaviour, water_alarm_template)
