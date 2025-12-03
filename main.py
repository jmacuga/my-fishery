import os
import time
from spade import DummyAgent

DEFAULT_HOST = os.getenv("DEFAULT_HOST", "server_hello")
AGENT_PASSWORD = os.getenv("AGENT_PASSWORD", "changeme")
AGENT_NAME = os.getenv("AGENT_NAME", "fisherman")

async def main():
    fisherman_agent = DummyAgent(f"{AGENT_NAME}@{DEFAULT_HOST}", AGENT_PASSWORD, verify_security=False)
    await fisherman_agent.start(auto_register=True)
    while True:
        try:
            await fisherman_agent.start(auto_register=True)
        except Exception:
            print("Failed to initialize agent, trying again...")
            time.sleep(3)



if __name__ == "__main__":
    main()
