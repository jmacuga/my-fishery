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
class TestCaretakersSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.container_name = "prosody_test_caretakers"
        cls.image = "prosodyim/prosody:13.0"
        cls.xmpp_domain = "localhost"

        subprocess.run(
            ["docker", "pull", cls.image],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

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

        accounts = [("owner", "ownerpass"), ("fish_caretaker", "fishpass")]
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

        logs_dir = Path(__file__).parent.parent / "logs"
        logs_dir.mkdir(exist_ok=True)
        cls.log_file = logs_dir / "fishery_system.log"
        try:
            if cls.log_file.exists():
                cls.log_file.unlink()
        except Exception:
            pass

        cls.proc_system = None

    @classmethod
    def tearDownClass(cls):
        try:
            if cls.proc_system and cls.proc_system.poll() is None:
                cls.proc_system.terminate()
                cls.proc_system.wait(timeout=5)
        except Exception:
            pass

        try:
            subprocess.run(
                ["docker", "stop", cls.container_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        except Exception:
            pass

    def test_feeder_runs_and_orders_when_low(self):
        py = sys.executable
        cwd = Path(__file__).parent.parent
        self.__class__.proc_system = subprocess.Popen(
            [py, "fishing_system.py"],
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        # wait for system start
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
        self.assertTrue(started, "System did not start in time")

        # wait some seconds to allow feeder behaviour to run
        time.sleep(6)

        # read logs
        log_text = ""
        try:
            with open(self.__class__.log_file, "r", encoding="utf-8") as f:
                log_text = f.read()
        except FileNotFoundError:
            self.fail("Log file not found; system may not have written logs")

        # check for feeding log or order log
        self.assertTrue(
            ("Feeding done" in log_text)
            or ("ordering food" in log_text.lower())
            or ("Food delivered" in log_text),
            "Expected feeder activity logs (feeding or ordering) not found",
        )


if __name__ == "__main__":
    unittest.main()
