import asyncio
import spade
from src import FisherAgent, OwnerAgent, WaterCaretakerAgent

SYSTEM_NAME = "SYSTEM"


async def main():
    owner_jid = "owner@localhost"
    owner_password = ""

    fisher_jid = "fisher@localhost"
    fisher_password = ""

    water_caretaker_jid = "water_caretaker@localhost"
    water_caretaker_password = ""

    fish_caretaker_jid = "fish_caretaker@localhost"
    fish_caretaker_password = ""

    owner = OwnerAgent(owner_jid, owner_password, fisher_jid, water_caretaker_jid)
    fisher = FisherAgent(fisher_jid, fisher_password, owner_jid)
    water_caretaker = WaterCaretakerAgent(
        water_caretaker_jid, water_caretaker_password, owner_jid, logs_out=True
    )

    # Start agentów
    agent_list = [owner, fisher, water_caretaker]
    await spade.start_agents(agent_list)

    print(f"[{SYSTEM_NAME}] Agenci wystartowali ({agent_list}).")

    # Czekamy, aż Fisher się zakończy
    while owner.is_alive():
        await asyncio.sleep(1)
        # if not fisher.is_alive():
        #     print(f"[{SYSTEM_NAME}] Fisher zakończył pracę, zatrzymuję Ownera.")
        #     await owner.stop()
        #     break

    print(f"[{SYSTEM_NAME}] Koniec.")


if __name__ == "__main__":
    spade.run(main())
