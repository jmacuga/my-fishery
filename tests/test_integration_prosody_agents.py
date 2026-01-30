import os
import shutil
import socket
import subprocess
import time
import unittest
from pathlib import Path
import sys
import asyncio

# allow importing project agents
sys.path.insert(0, str(Path(__file__).parent.parent))

# Integration test is opt-in to avoid surprising CI environments
RUN_INTEGRATION = os.environ.get("RUN_PROSODY_INTEGRATION", "0") == "1"
DOCKER_BIN = shutil.which("docker") is not None


@unittest.skipUnless(
    RUN_INTEGRATION and DOCKER_BIN,
    "Integration test requires RUN_PROSODY_INTEGRATION=1 and docker",
)
class TestProsodyAndAgentsIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.container_name = "prosody_test_integration"
        cls.image = "prosodyim/prosody:13.0"
        cls.xmpp_domain = "localhost"

        # Pull image (best-effort)
        subprocess.run(
            ["docker", "pull", cls.image],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Run prosody container mapped to host 5222
        run_cmd = [
            "docker",
            "run",
            "--rm",
            "-d",
            "--name",
            cls.container_name,
            # set virtual hosts so prosody serves the expected XMPP domain
            "-e",
            f"PROSODY_VIRTUAL_HOSTS={cls.xmpp_domain}",
            "-p",
            "5222:5222",
            cls.image,
        ]
        proc = subprocess.run(run_cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"Failed to start prosody container: {proc.stderr}")

        cls.container_id = proc.stdout.strip()

        # wait for port 5222 to become reachable
        deadline = time.time() + 30
        while time.time() < deadline:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.settimeout(1.0)
                    s.connect(("localhost", 5222))
                    break
                except Exception:
                    time.sleep(0.5)
        else:
            cls.tearDownClass()
            raise RuntimeError("Prosody did not start listening on 5222 in time")

        # register a few accounts inside the container using prosodyctl
        accounts = [
            ("owner", "ownerpass"),
            ("water", "waterpass"),
            ("fish", "fishpass"),
            ("fisher1", "fisherpass"),
        ]

        for user, pwd in accounts:
            cmd = [
                "docker",
                "exec",
                cls.container_name,
                "prosodyctl",
                "register",
                user,
                cls.xmpp_domain,
                pwd,
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    @classmethod
    def tearDownClass(cls):
        # stop container if running
        try:
            subprocess.run(
                ["docker", "stop", cls.container_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        except Exception:
            pass

    def test_agents_start_and_stop(self):
        """Run the async agent start/stop flow inside an asyncio loop so unittest collects it."""

        async def _run():
            # Import spade and project agents lazily so the test can be skipped earlier
            try:
                from spade import agent as spade_agent  # noqa: F401
            except Exception as e:
                self.skipTest(f"spade not importable: {e}")

            from src.owner_agent import OwnerAgent
            from src.fish_caretaker_agent import FishCaretakerAgent
            from src.water_caretaker_agent import WaterCaretakerAgent

            # create agents with credentials we registered
            owner_jid = f"owner@{self.xmpp_domain}"
            water_jid = f"water@{self.xmpp_domain}"
            fish_jid = f"fish@{self.xmpp_domain}"

            owner = OwnerAgent(owner_jid, "ownerpass", water_jid, fish_jid)
            water = WaterCaretakerAgent(water_jid, "waterpass", owner_jid)
            fish = FishCaretakerAgent(fish_jid, "fishpass", owner_jid)

            # Start agents (these will attempt XMPP connection to prosody)
            try:
                await owner.start()
                await water.start()
                await fish.start()

                # Basic sanity checks: agents should be running
                self.assertTrue(owner.is_alive())
                self.assertTrue(water.is_alive())
                self.assertTrue(fish.is_alive())

            finally:
                # Stop agents
                try:
                    await owner.stop()
                except Exception:
                    pass
                try:
                    await water.stop()
                except Exception:
                    pass
                try:
                    await fish.stop()
                except Exception:
                    pass

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
