# Quick Start Guide

## Setup (One Time)

1. Install Prosody:

   ```bash
   sudo apt install prosody
   sudo prosodyctl start
   ```

2. Create Prosody users:

   ```bash
   sudo prosodyctl adduser owner@localhost
   sudo prosodyctl adduser fisher1@localhost
   sudo prosodyctl adduser fisher2@localhost
   sudo prosodyctl adduser fisher3@localhost
   sudo prosodyctl adduser water_caretaker@localhost
   sudo prosodyctl adduser fish_caretaker@localhost
   ```

3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the System

### Step 1: Start Main System

Open **Terminal 1** and run:

```bash
python run_system.py
```

You should see:

```
FISHERY SYSTEM - Main Services Running
✓ OwnerAgent: owner@localhost
✓ WaterCaretaker: water_caretaker@localhost
✓ FishCaretaker: fish_caretaker@localhost
✓ Fisherman limit: 10
```

### Step 2: Start Fishermen

Open **separate terminals** for each fisherman:

**Terminal 2:**

```bash
python run_fisherman.py 1
```

**Terminal 3:**

```bash
python run_fisherman.py 2
```

**Terminal 4:**

```bash
python run_fisherman.py 3
```

Each fisherman will show their own interactive menu.

### Step 3: (Optional) View Logs

Open another terminal:

```bash
./view_logs.sh
```

## Using the Fishermen

Each fisherman has an interactive menu:

- **1** - Request to enter fishery
- **2** - Request taking fish (must be in fishery)
- **3** - Show status
- **4** - Exit fishery
- **0** - Exit program

## Tips

- Each fisherman runs independently
- The system enforces a limit (default: 10 fishermen)
- When the limit is reached, new entrance requests are refused
- All actions are logged to `logs/fishery_system.log`

## Troubleshooting

**Problem**: "Connection refused" or "Agent not found"

- **Solution**: Make sure Prosody is running: `sudo prosodyctl status`
- **Solution**: Make sure you created the Prosody user for that agent

**Problem**: "Permission denied" when entering fishery

- **Solution**: Check if the fisherman limit is reached (default: 10)
- **Solution**: Check if you're already in the fishery

**Problem**: Multiple fishermen in one terminal cause input conflicts

- **Solution**: Run each fisherman in a separate terminal (recommended)
