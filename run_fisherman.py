"""
Run a single fisherman agent in a separate terminal.
Usage: python run_fisherman.py <fisherman_number>
Example: python run_fisherman.py 1
"""
import sys
import asyncio
import spade
from src import FisherAgent
from src.logger_config import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger("FishermanRunner")


async def main(fisherman_number):
    owner_jid = "owner@localhost"
    owner_password = ""

    fisher_jid = f"fisher{fisherman_number}@localhost"
    fisher_password = ""

    fish_caretaker_jid = "fish_caretaker@localhost"

    # Create fisherman agent
    fisher = FisherAgent(
        fisher_jid, fisher_password, owner_jid, fish_caretaker_jid=fish_caretaker_jid
    )

    # Start fisherman agent
    await spade.start_agents([fisher])

    logger.info(f"Fisherman agent {fisher_jid} started")
    logger.info("Waiting for user input...")

    # Keep running until stopped
    try:
        while fisher.is_alive():
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info(f"Shutting down fisherman {fisher_jid}...")
        await fisher.stop()

    logger.info(f"Fisherman {fisher_jid} stopped")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_fisherman.py <fisherman_number>")
        print("Example: python run_fisherman.py 1")
        sys.exit(1)
    
    try:
        fisherman_number = int(sys.argv[1])
        if fisherman_number < 1:
            print("Error: Fisherman number must be >= 1")
            sys.exit(1)
    except ValueError:
        print("Error: Fisherman number must be an integer")
        sys.exit(1)

    spade.run(main(fisherman_number))

