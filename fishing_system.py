import asyncio
import spade
from src import FisherAgent, OwnerAgent


async def main():
    # Dane logowania – musisz wcześniej założyć konta na serwerze XMPP
    owner_jid = "owner@localhost"
    owner_password = ""

    fisher_jid = "fisher@localhost"
    fisher_password = ""

    # Tworzymy agenty
    owner = OwnerAgent(owner_jid, owner_password)
    fisher = FisherAgent(fisher_jid, fisher_password, owner_jid)

    # Wstrzykujemy JID ownera do fishera (nasza „konfiguracja protokołu”)

    # Start agentów
    agent_list = [owner, fisher]
    await spade.start_agents(agent_list)

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
    spade.run(main())
