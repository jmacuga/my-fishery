import os
import shutil
import socket
import subprocess
import time
import unittest
from pathlib import Path
import sys

# Integration test is opt-in to avoid surprising CI environments
RUN_INTEGRATION = os.environ.get("RUN_PROSODY_INTEGRATION", "0") == "1"
DOCKER_BIN = shutil.which("docker") is not None


@unittest.skipUnless(
    RUN_INTEGRATION and DOCKER_BIN,
    "Integration test requires RUN_PROSODY_INTEGRATION=1 and docker",
)
class TestOwnerFisherIntegrationScripts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.container_name = "prosody_test_owner_fisher"
        cls.image = "prosodyim/prosody:13.0"
        cls.xmpp_domain = "localhost"

        # Pull image
        subprocess.run(
            ["docker", "pull", cls.image],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Start prosody container
        run_cmd = [
            "docker",
            "run",
            "--rm",
            "-d",
            "--name",
            cls.container_name,
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

        # wait for prosody to listen
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

        # register accounts used by scripts
        accounts = [
            ("owner", "ownerpass"),
            ("water_caretaker", "waterpass"),
            ("fish_caretaker", "fishpass"),
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

        # ensure logs dir exists and is fresh
        logs_dir = Path(__file__).parent.parent / "logs"
        logs_dir.mkdir(exist_ok=True)
        cls.log_file = logs_dir / "fishery_system.log"
        try:
            if cls.log_file.exists():
                cls.log_file.unlink()
        except Exception:
            pass

        cls.proc_system = None
        cls.proc_fisher = None

    @classmethod
    def tearDownClass(cls):
        # terminate processes
        for p in (getattr(cls, "proc_fisher", None), getattr(cls, "proc_system", None)):
            try:
                if p and p.poll() is None:
                    p.terminate()
                    p.wait(timeout=5)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass

        # stop docker container
        try:
            subprocess.run(
                ["docker", "stop", cls.container_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        except Exception:
            pass

    def test_run_system_and_fisher_interaction(self):
        # start fishing_system.py as a subprocess
        py = sys.executable
        cwd = Path(__file__).parent.parent
        self.__class__.proc_system = subprocess.Popen(
            [py, "fishing_system.py"],
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        # wait for system to print ready message
        deadline = time.time() + 30
        started = False
        while time.time() < deadline:
            line = self.__class__.proc_system.stdout.readline()
            if not line:
                time.sleep(0.1)
                continue
            if "FISHERY SYSTEM - Main Services Running" in line:
                started = True
                break
        self.assertTrue(started, "Fishing system did not start in time")

        # start a fisherman process and simulate input
        self.__class__.proc_fisher = subprocess.Popen(
            [py, "run_fisherman.py", "1"],
            cwd=str(cwd),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        # helper to send input
        def send_input(s):
            try:
                self.__class__.proc_fisher.stdin.write(s)
                self.__class__.proc_fisher.stdin.flush()
            except Exception:
                pass

        # 1) Request to enter fishery
        send_input("1\n")
        time.sleep(1)

        # 2) Take fish 3 times
        for _ in range(3):
            send_input("2\n")
            time.sleep(1)

        # 3) Try entering again (should be already inside)
        send_input("1\n")
        time.sleep(1)

        # 4) Exit fishery
        send_input("4\n")
        # send exit program to stop loop
        send_input("0\n")

        # wait for fisherman to exit (give it some time)
        try:
            self.__class__.proc_fisher.wait(timeout=10)
        except Exception:
            try:
                self.__class__.proc_fisher.terminate()
            except Exception:
                pass

        # give system a bit to log events
        time.sleep(2)

        # read logs and assert expected entries
        log_text = ""
        try:
            with open(self.__class__.log_file, "r", encoding="utf-8") as f:
                log_text = f.read()
        except FileNotFoundError:
            self.fail("Log file not found; system may not have written logs")

        # assert that owner granted permissions at least once
        grants = log_text.count("Permission granted. Fishes taken today")
        self.assertGreaterEqual(
            grants, 1, f"Expected at least 1 permission granted entry, got {grants}"
        )

        # assert fisher attempted entering twice (local log from FisherAgent)
        attempted_enter_msg = "Attempted to enter fishery while already inside"
        self.assertIn(attempted_enter_msg, log_text)


if __name__ == "__main__":
    unittest.main()
