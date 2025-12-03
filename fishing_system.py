import asyncio
from spade import agent, behaviour, message


########################
# Agent Fisher (wędkarz)
########################

class FisherAgent(agent.Agent):
    class AskPermissionBehaviour(behaviour.CyclicBehaviour):
        async def on_start(self):
            print("[FISHER] Startuję zachowanie i za chwilę wyślę prośbę o wejście na łowisko.")
            # Wyślij od razu po starcie
            await self.ask_owner()

        async def ask_owner(self):
            msg = message.Message(
                to=self.agent.owner_jid,   # JID Ownera
                body="Czy mogę wejść na łowisko?",
                metadata={
                    "performative": "request",
                    "protocol": "fishing-access"
                }
            )
            print(f"[FISHER] Wysyłam zapytanie do {self.agent.owner_jid}")
            await self.send(msg)

        async def run(self):
            # Czekamy na odpowiedź od Ownera
            msg = await self.receive(timeout=10)  # sekund
            if msg:
                performative = msg.metadata.get("performative", "")
                print(f"[FISHER] Otrzymałem wiadomość: '{msg.body}' (performative: {performative})")

                if performative == "agree":
                    print("[FISHER] Super, dostałem zgodę na wejście na łowisko!")
                    # Możesz tutaj dodać dalszą logikę (np. łowienie)
                elif performative == "refuse":
                    print("[FISHER] Niestety, Owner odmówił wejścia na łowisko.")
                else:
                    print("[FISHER] Nieznany typ odpowiedzi.")

                # Kończymy zachowanie i agenta po otrzymaniu pierwszej odpowiedzi
                self.kill()
                await self.agent.stop()
            else:
                print("[FISHER] Nie otrzymałem żadnej odpowiedzi w czasie timeoutu.")
                # Możesz ponowić prośbę albo zakończyć
                self.kill()
                await self.agent.stop()

    async def setup(self):
        print(f"[FISHER] Agent {self.jid} startuje.")
        b = self.AskPermissionBehaviour()
        self.add_behaviour(b)
        # Można przechowywać JID Ownera jako „konfigurację”
        # (tutaj zakładamy, że jest ustawiony przed uruchomieniem)
        # self.owner_jid = "owner@localhost"


########################
# Agent Owner (właściciel łowiska)
########################

class OwnerAgent(agent.Agent):
    class HandleRequestsBehaviour(behaviour.CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=30)  # czekamy na request
            if msg:
                performative = msg.metadata.get("performative", "")
                protocol = msg.metadata.get("protocol", "")
                print(f"[OWNER] Otrzymałem wiadomość od {msg.sender}: '{msg.body}' "
                      f"(performative: {performative}, protocol: {protocol})")

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
                        print("[OWNER] Wysyłam zgodę.")
                    else:
                        reply.body = "Nie możesz teraz wejść na łowisko."
                        reply.metadata["performative"] = "refuse"
                        print("[OWNER] Wysyłam odmowę.")

                    await self.send(reply)

                else:
                    print("[OWNER] To nie jest wiadomość zgodna z naszym protokołem.")

            else:
                print("[OWNER] Brak nowych wiadomości...")

    async def setup(self):
        print(f"[OWNER] Agent {self.jid} startuje.")
        b = self.HandleRequestsBehaviour()
        self.add_behaviour(b)


########################
# Funkcja main – uruchomienie
########################

async def main():
    # Dane logowania – musisz wcześniej założyć konta na serwerze XMPP
    owner_jid = "owner@localhost"
    owner_password = ""

    fisher_jid = "fisher@localhost"
    fisher_password = ""

    # Tworzymy agenty
    owner = OwnerAgent(owner_jid, owner_password)
    fisher = FisherAgent(fisher_jid, fisher_password)

    # Wstrzykujemy JID ownera do fishera (nasza „konfiguracja protokołu”)
    fisher.owner_jid = owner_jid

    # Start agentów
    await owner.start()
    await fisher.start()

    print("[SYSTEM] Agenci wystartowali (Owner i Fisher).")

    # Czekamy, aż Fisher się zakończy
    while owner.is_alive():
        await asyncio.sleep(1)
        if not fisher.is_alive():
            print("[SYSTEM] Fisher zakończył pracę, zatrzymuję Ownera.")
            await owner.stop()
            break

    print("[SYSTEM] Koniec.")


if __name__ == "__main__":
    asyncio.run(main())
