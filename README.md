# 🐟 My Fishery

> **A multi-agent system for intelligent, autonomous fishery management**

"My Fishery" is a distributed agent-based simulation that models a real-world aquaculture operation — from fisherman access control and catch quotas to water-quality monitoring, fish-stock analytics, and automated feeding. Agents communicate over **XMPP** using the **SPADE** framework, coordinating decisions asynchronously without a central orchestrator.

Built to demonstrate **multi-agent systems (MAS)**, **event-driven architecture**, and **domain-driven agent design** in Python.

---

## ✨ Why This Project?

Modern fisheries need more than static dashboards — they need systems that **sense, decide, and act** in real time. MY Fishery explores that idea by assigning each responsibility to a dedicated autonomous agent that negotiates with peers through structured protocols.

| Challenge                     | Agent-based solution                                                      |
| ----------------------------- | ------------------------------------------------------------------------- |
| Who can enter the fishery?    | **Owner Agent** enforces capacity limits and tracks active fishermen      |
| Is the water safe?            | **Water Caretaker** monitors pH and triggers aeration on anomalies        |
| Are fish stocks healthy?      | **Fish Caretaker** analyses camera & sonar data, raises restocking alarms |
| Can a fisherman keep a catch? | Permission flow between **Fisherman → Owner → Fish Caretaker**            |
| Who feeds the fish?           | **Fish Caretaker** manages feeding schedules and food inventory           |

---

## 🏗️ Architecture

```mermaid
flowchart TB
    subgraph Fishermen["🎣 Fisherman Agents"]
        F1[fisher1@localhost]
        F2[fisher2@localhost]
        F3[fisher3@localhost]
    end

    subgraph Core["⚙️ Core Services"]
        O[Owner Agent]
        WC[Water Caretaker]
        FC[Fish Caretaker]
    end

    XMPP[(Prosody XMPP Server)]

    F1 & F2 & F3 <-->|FIPA ACL messages| XMPP
    O & WC & FC <-->|FIPA ACL messages| XMPP

    F1 & F2 & F3 -->|enter / take fish / exit| O
    F1 & F2 & F3 -->|register catch data| FC
    WC -->|water quality alarm| O
    FC -->|stocking alarm| O
    WC -.->|auto-aeration| WC
    FC -.->|feeding & food orders| FC
```

Each agent runs as an independent **asyncio** process. Fishermen connect on demand — mirroring how real distributed IoT/edge systems scale.

---

## 🚀 Key Features

### Multi-Agent Coordination

- **SPADE** agents communicating via **XMPP** (Prosody) with FIPA-style performatives (`query_if`, `agree`, `refuse`, `inform`)
- **Protocol-driven messaging** — every interaction mapped to a named protocol (`if_can_enter`, `register_fish_data`, `send_water_quality_alarm`, …)
- **Conversation tracking** with `conversation-id` and `reply-with` for reliable request/response flows

### Smart Environmental Monitoring

- **Water Caretaker** collects pH readings and computes **z-score anomaly detection** on rolling windows
- Automatic **aeration response** when water quality deviates beyond threshold
- **Fish Caretaker (DEI)** fuses camera + sonar sensor streams to detect low stock levels

### Resource & Access Management

- Configurable **fisherman capacity** (default: 10) and **daily catch quota** (default: 50)
- Entrance deduplication — prevents double-counting fishermen already on site
- Exit registration with full session bookkeeping

### Automated Fish Care

- Periodic **feeding behaviour** with portion control and supply tracking
- **Low-inventory detection** triggers simulated food re-ordering
- Catch data registration per fisherman for stock analytics

### Developer Experience

- **Rich terminal UI** — interactive menus and status tables for Owner and Fisherman agents
- **Structured logging** to `logs/fishery_system.log` with a convenience `view_logs.sh` script
- **Comprehensive test suite** — unit tests + integration tests covering agent lifecycles, protocol flows, and caretaker behaviours

---

## 🛠️ Tech Stack

| Layer                 | Technology                                        |
| --------------------- | ------------------------------------------------- |
| Language              | Python 3.12                                       |
| Multi-Agent Framework | [SPADE](https://github.com/javipalanca/spade) 4.x |
| Messaging             | XMPP via Prosody                                  |
| Async Runtime         | asyncio + uvloop                                  |
| Terminal UI           | Rich                                              |
| Testing               | pytest                                            |
| Dependency Management | uv (pip-compile)                                  |

---

## 📡 Agent Roles

| Agent               | JID                         | Responsibility                                                      |
| ------------------- | --------------------------- | ------------------------------------------------------------------- |
| **Owner**           | `owner@localhost`           | Access control, catch quotas, alarm handling, interactive dashboard |
| **Water Caretaker** | `water_caretaker@localhost` | pH monitoring, anomaly detection, aeration                          |
| **Fish Caretaker**  | `fish_caretaker@localhost`  | Stock monitoring, feeding, catch registration, restocking alerts    |
| **Fisherman**       | `fisher{N}@localhost`       | Enter/exit fishery, request catch permission, report catches        |

---

## ⚡ Quick Start

### Prerequisites

- **Python 3.12.4**
- **Prosody** XMPP server

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set up Prosody

```bash
sudo apt install prosody
sudo mkdir -p /run/prosody
sudo chown prosody:prosody /run/prosody
sudo prosodyctl start
```

Create the required agent accounts:

```bash
sudo prosodyctl adduser owner@localhost
sudo prosodyctl adduser fisher1@localhost
sudo prosodyctl adduser fisher2@localhost
sudo prosodyctl adduser fisher3@localhost
sudo prosodyctl adduser water_caretaker@localhost
sudo prosodyctl adduser fish_caretaker@localhost
```

> Add more fishermen as needed (up to the limit set in `OwnerAgent`).

Verify Prosody is running:

```bash
sudo prosodyctl status
```

### 3. Run the system

The system uses **separate processes** for core services and fishermen — giving you full control over each agent.

**Terminal 1 — Core services** (Owner + Caretakers):

```bash
python fishing_system.py
```

**Terminal 2, 3, 4… — Fisherman agents**:

```bash
python run_fisherman.py 1
python run_fisherman.py 2
python run_fisherman.py 3
```

**Optional — Live log tail**:

```bash
./view_logs.sh
# or
tail -f logs/fishery_system.log
```

---

## 🧪 Running Tests

```bash
pip install -r requirements.dev.txt
pytest
```

The test suite covers individual agent logic, protocol handlers, z-score calculations, feeding behaviours, and end-to-end integration scenarios.

---

## 📂 Project Structure

```
my_fishery/
├── fishing_system.py          # Main entry — Owner + Caretakers
├── run_fisherman.py           # Launch individual fisherman agents
├── src/
│   ├── owner_agent.py         # Access control & quotas
│   ├── fisher_agent.py        # Fisherman interactions
│   ├── water_caretaker_agent.py
│   ├── fish_caretaker_agent.py
│   ├── protocols.py           # Message protocol definitions
│   ├── misc.py                # Z-score & data utilities
│   └── logger_config.py
├── tests/                     # Unit & integration tests
└── logs/                      # Runtime logs
```

---

## 🔮 Design Highlights for Reviewers

- **Separation of concerns** — each agent owns a single domain (water, fish, access, fishing)
- **Loose coupling** — agents interact only through well-defined XMPP protocols, not shared state
- **Statistical monitoring** — z-score-based anomaly detection rather than hard-coded thresholds
- **Production-minded patterns** — async I/O, structured logging, templated message routing, and testable behaviours
- **Extensible** — new agent types or protocols can be added without modifying existing agents

---

<p align="center">
  <sub>Built with Python · SPADE · asyncio · Rich</sub>
</p>
