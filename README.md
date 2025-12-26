## MY Fishery

### Requirements

python 3.12.4

### Set up

sudo apt install prosody

sudo prosodyctl start

sudo cat /var/log/prosody/prosody.log

sudo mkdir -p /run/prosody
sudo chown prosody:prosody /run/prosody

sudo prosodyctl adduser owner@localhost
sudo prosodyctl adduser fisher1@localhost
sudo prosodyctl adduser fisher2@localhost
sudo prosodyctl adduser fisher3@localhost

# Add more fishermen as needed (up to the limit set in OwnerAgent)

sudo prosodyctl adduser water_caretaker@localhost
sudo prosodyctl adduser fish_caretaker@localhost

### Run

sudo mkdir -p /run/prosody
sudo chown prosody:prosody /run/prosody

sudo prosodyctl start
sudo prosodyctl status

### Running the System

The system is designed to run with separate processes for better control:

#### Option 1: Separate Terminals (Recommended)

1. **Terminal 1** - Start the main system (OwnerAgent + Caretakers):

   ```bash
   python fishing_system.py
   ```

   This runs the OwnerAgent, WaterCaretaker, and FishCaretaker.

2. **Terminal 2, 3, 4...** - Start individual fisherman agents:

   ```bash
   # Terminal 2
   python run_fisherman.py 1

   # Terminal 3
   python run_fisherman.py 2

   # Terminal 4
   python run_fisherman.py 3
   ```

   Each fisherman runs in its own terminal with an interactive interface.

3. **Log Terminal** - View system logs (optional):
   ```bash
   ./view_logs.sh
   ```
   Or manually:
   ```bash
   tail -f logs/fishery_system.log
   ```
