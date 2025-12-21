from spade import message
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour


class FisherAgent(Agent):
    def __init__(self, jid, password, owner_jid):
        super().__init__(jid, password)
        self.owner_jid = owner_jid

    class AskPermissionBehaviour(CyclicBehaviour):
        async def on_start(self):
            print(
                f"[{self.__class__.__name__}] Startuję zachowanie i za chwilę wyślę prośbę o wejście na łowisko."
            )
            # Wyślij od razu po starcie
            await self.ask_owner()

        async def ask_owner(self):
            msg = message.Message(
                to=self.agent.owner_jid,  # JID Ownera
                body="Czy mogę wejść na łowisko?",
                metadata={"performative": "request", "protocol": "fishing-access"},
            )
            print(
                f"[{self.__class__.__name__}] Wysyłam zapytanie do {self.agent.owner_jid}"
            )
            await self.send(msg)

        async def run(self):
            # Czekamy na odpowiedź od Ownera
            msg = await self.receive(timeout=10)  # sekund
            if msg:
                performative = msg.metadata.get("performative", "")
                print(
                    f"[{self.__class__.__name__}] Otrzymałem wiadomość: '{msg.body}' (performative: {performative})"
                )

                if performative == "agree":
                    print(
                        f"[{self.__class__.__name__}] Super, dostałem zgodę na wejście na łowisko!"
                    )
                    # Możesz tutaj dodać dalszą logikę (np. łowienie)
                elif performative == "refuse":
                    print(
                        f"[{self.__class__.__name__}] Niestety, Owner odmówił wejścia na łowisko."
                    )
                else:
                    print(f"[{self.__class__.__name__}] Nieznany typ odpowiedzi.")

                # Kończymy zachowanie i agenta po otrzymaniu pierwszej odpowiedzi
                self.kill()
                await self.agent.stop()
            else:
                print(
                    f"[{self.__class__.__name__}] Nie otrzymałem żadnej odpowiedzi w czasie timeoutu."
                )
                # Możesz ponowić prośbę albo zakończyć
                self.kill()
                await self.agent.stop()

    async def setup(self):
        print(f"[{self.__class__.__name__}] Agent {self.jid} startuje.")
        b = self.AskPermissionBehaviour()
        self.add_behaviour(b)
        # Można przechowywać JID Ownera jako „konfigurację”
        # (tutaj zakładamy, że jest ustawiony przed uruchomieniem)
        # self.owner_jid = "owner@localhost"
