"""
Main system script - runs OwnerAgent, WaterCaretaker, and FishCaretaker.
Fisherman agents should be run separately using run_fisherman.py
"""
import os
import asyncio
import spade
from src import OwnerAgent, WaterCaretakerAgent, FishCaretakerAgent
from src.logger_config import setup_logging, get_logger
from dotenv import load_dotenv

load_dotenv()
setup_logging()
SYSTEM_NAME = os.environ.get("SYSTEM_NAME", "SYSTEM")



async def main():
    owner_jid = "owner@localhost"
    owner_password = ""

    water_caretaker_jid = "water_caretaker@localhost"
    water_caretaker_password = ""

    fish_caretaker_jid = "fish_caretaker@localhost"
    fish_caretaker_password = ""

    # Create owner and caretaker agents (no fishermen here)
    owner = OwnerAgent(owner_jid, owner_password, water_caretaker_jid, fish_caretaker_jid)
    water_caretaker = WaterCaretakerAgent(
        water_caretaker_jid, water_caretaker_password, owner_jid)
    fish_caretaker = FishCaretakerAgent(fish_caretaker_jid, fish_caretaker_password, owner_jid)

    # Start system agents
    agent_list = [owner, water_caretaker, fish_caretaker]
    await spade.start_agents(agent_list)

    system_logger = get_logger("System")
    system_logger.info(f"System agents started ({len(agent_list)} agents)")
    system_logger.info("OwnerAgent, WaterCaretaker, and FishCaretaker are running")
    system_logger.info(f"Fisherman limit: {owner.fisherman_limit}")
    system_logger.info("Waiting for fisherman agents to connect...")
    
    print("\n" + "=" * 60)
    print("FISHERY SYSTEM - Main Services Running")
    print("=" * 60)
    print(f"✓ OwnerAgent: {owner_jid}")
    print(f"✓ WaterCaretaker: {water_caretaker_jid}")
    print(f"✓ FishCaretaker: {fish_caretaker_jid}")
    print(f"✓ Fisherman limit: {owner.fisherman_limit}")
    print("\nTo add fishermen, run in separate terminals:")
    print("  python run_fisherman.py 1")
    print("  python run_fisherman.py 2")
    print("  python run_fisherman.py 3")
    print("=" * 60 + "\n")

    # Keep the system running until stopped
    try:
        while owner.is_alive():
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        system_logger.info("Shutting down system...")
        await owner.stop()
        await water_caretaker.stop()
        await fish_caretaker.stop()

    system_logger.info("System stopped")


if __name__ == "__main__":
    spade.run(main())

