from spade import message
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour


class OwnerAgent(Agent):
    class HandleRequestsBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=30)  # czekamy na request
            if msg:
                performative = msg.metadata.get("performative", "")
                protocol = msg.metadata.get("protocol", "")
                print(
                    f"[{self.__class__.__name__}] Otrzymałem wiadomość od {msg.sender}: '{msg.body}' "
                    f"(performative: {performative}, protocol: {protocol})"
                )

                # Sprawdzamy, czy to pasuje do naszego „protokołu”
                if performative == "request" and protocol == "fishing-access":
                    # Tutaj możesz dodać dowolną logikę decyzji:
                    # np. sprawdzenie pory dnia, limitu osób, itp.
                    allow = True  # na razie zawsze pozwalamy

                    reply = msg.make_reply()
                    reply.metadata["protocol"] = protocol

                    if allow:
                        reply.body = "Tak, możesz wejść na łowisko."
                        reply.metadata["performative"] = "agree"
                        print(f"[{self.__class__.__name__}] Wysyłam zgodę.")
                    else:
                        reply.body = "Nie możesz teraz wejść na łowisko."
                        reply.metadata["performative"] = "refuse"
                        print(f"[{self.__class__.__name__}] Wysyłam odmowę.")

                    await self.send(reply)

                else:
                    print(
                        f"[{self.__class__.__name__}] To nie jest wiadomość zgodna z naszym protokołem."
                    )

            else:
                print(f"[{self.__class__.__name__}] Brak nowych wiadomości...")

    async def setup(self):
        print(f"[{self.__class__.__name__}] Agent {self.jid} startuje.")
        b = self.HandleRequestsBehaviour()
        self.add_behaviour(b)
