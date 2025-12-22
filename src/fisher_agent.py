from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.template import Template
from spade.message import Message


class FisherAgent(Agent):
    def __init__(self, jid, password, owner_jid):
        super().__init__(jid, password)
        self.owner_jid = owner_jid

    class AskPermissionBehaviour(CyclicBehaviour):
        async def on_start(self):
            print(
                f"[{self.agent.__class__.__name__}] Starting behaviour and will soon send a request to enter the fishery."
            )
            await self.ask_owner()

        async def ask_owner(self):
            msg = Message(
                to=self.agent.owner_jid,
                body="May I enter the fishery?",
                metadata={"performative": "request", "protocol": "fishing-access"},
            )
            print(
                f"[{self.agent.__class__.__name__}] Sending request to {self.agent.owner_jid}"
            )
            await self.send(msg)

        async def run(self):
            msg = await self.receive(timeout=10)
            if msg:
                performative = msg.metadata.get("performative", "")
                print(
                    f"[{self.agent.__class__.__name__}] Received message: '{msg.body}' (performative: {performative})"
                )

                if performative == "agree":
                    print(
                        f"[{self.agent.__class__.__name__}] Great, I received permission to enter the fishery!"
                    )
                elif performative == "refuse":
                    print(
                        f"[{self.agent.__class__.__name__}] Unfortunately, the Owner denied entry to the fishery."
                    )
                else:
                    print(f"[{self.agent.__class__.__name__}] Unknown response type.")

                self.kill()
                await self.agent.stop()
            else:
                print(
                    f"[{self.agent.__class__.__name__}] I did not receive any response within the timeout."
                )
                self.kill()
                await self.agent.stop()

    async def setup(self):
        print(f"[{self.__class__.__name__}] Agent {self.jid} starting.")

        b = self.AskPermissionBehaviour()
        self.add_behaviour(b)
