import json
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.template import Template
from .logger_config import get_logger
from .protocols import Protocols
from uuid import uuid4 as uuid

import asyncio
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

import asyncio
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

logger = get_logger("OwnerAgent")

console = Console()


class RichMenuBehaviourMixin:
    """
    Mixin z logiką menu identyczną jak w FisherAgent:
    - Panel z menu
    - async input przez run_in_executor
    - prosta pętla wyboru akcji
    """

    MENU_TITLE = "AGENT"
    BORDER_STYLE = "cyan"

    def menu_items(self) -> list[tuple[str, str]]:
        """
        Zwraca listę (key, opis). Np: [("1","Pokaż status"), ...]
        """
        return []

    def render_menu(self):
        agent_name = str(self.agent.jid).split("@")[0]
        items = "\n".join(
            [f"[bold cyan]{k}[/bold cyan] - {desc}" for k, desc in self.menu_items()]
        )
        menu_text = f"""
{items}

[dim]Agent: {agent_name}[/dim]
        """
        console.print(
            Panel(
                menu_text,
                title=f"[bold green]{self.MENU_TITLE}[/bold green] - {agent_name.upper()} - Available Actions",
                border_style=self.BORDER_STYLE,
                padding=(1, 2),
            )
        )

    async def read_choice(self) -> str:
        loop = asyncio.get_event_loop()
        choice = await loop.run_in_executor(
            None, lambda: console.input("[bold cyan]Enter action number: [/bold cyan]")
        )
        return choice.strip()


from spade.behaviour import CyclicBehaviour


class OwnerUserGUI(CyclicBehaviour, RichMenuBehaviourMixin):
    MENU_TITLE = "OWNER AGENT"
    BORDER_STYLE = "magenta"

    async def on_start(self):
        await asyncio.sleep(2)
        self.render_menu()

        self._input_future = None
        self._awaiting_stocking_answer = False
        console.print("[bold cyan]Enter action number:[/bold cyan] ", end="")

    def menu_items(self):
        return [
            ("1", "Show status"),
            ("2", "Show active fishermen list"),
            ("0", "Exit program"),
        ]

    async def run(self):
        loop = asyncio.get_running_loop()

        try:
            # === 0) Jeśli czekamy na odpowiedź stocking, to NIE uruchamiamy nowego inputa ===
            if self._awaiting_stocking_answer:
                # czekamy aż ten sam future zwróci linię
                if self._input_future is not None and self._input_future.done():
                    ans = (self._input_future.result() or "").strip().lower()
                    self._input_future = None
                    self._awaiting_stocking_answer = False

                    if ans in ("y", "yes", "n", "no"):
                        console.print("[green][/green]")
                        self.agent.recommend_stocking()
                    else:
                        console.print("[red]Restocking rejected[/red]")

                    self.render_menu()
                    console.print(
                        "[bold cyan]Enter action number:[/bold cyan] ", end=""
                    )
                else:
                    await asyncio.sleep(0.1)
                return

            # === 1) Najpierw sprawdź alarm ZANIM wystartujesz menu input ===
            if self.agent.pending_stocking_prompt.is_set():
                self.agent.pending_stocking_prompt.clear()

                payload = self.agent.last_stocking_alarm or {}
                console.print("\n")
                console.print(
                    Panel(
                        f"[bold yellow]Fish stock low![/bold yellow]\n"
                        f"{payload}\n\n"
                        f"[bold]Do you want to restock? (y/n)[/bold]\n"
                        f"[dim]Write answer and press Enter[/dim]",
                        title="STOCKING DECISION",
                        border_style="yellow",
                    )
                )

                # jeśli menu input już działa, użyj go jako "odpowiedzi"
                if self._input_future is None:
                    self._input_future = loop.run_in_executor(
                        None, lambda: console.input("> ")
                    )

                self._awaiting_stocking_answer = True
                return

            # === 2) Normalny tryb: uruchom input menu tylko jeśli nie ma ===
            if self._input_future is None:
                self._input_future = loop.run_in_executor(
                    None, lambda: console.input("")
                )

            # jeśli user wpisał już wybór
            if self._input_future.done():
                choice = (self._input_future.result() or "").strip()
                self._input_future = None

                if choice == "1":
                    self.show_status()
                elif choice == "2":
                    self.show_fishermen()
                elif choice == "3":
                    self.agent.recommend_stocking()
                    console.print(
                        "[yellow]Stocking recommendation triggered (see logs).[/yellow]"
                    )
                elif choice == "0":
                    console.print("[yellow]Exiting...[/yellow]")
                    await self.agent.stop()
                    self.kill()
                    return
                elif choice:
                    console.print("[red]Invalid input. Please choose from menu.[/red]")

                self.render_menu()
                console.print("[bold cyan]Enter action number:[/bold cyan] ", end="")
                return

            await asyncio.sleep(0.1)

        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Exiting...[/yellow]")
            await self.agent.stop()
            self.kill()

    def show_status(self):
        t = Table(title="Owner Status", show_header=True, header_style="bold magenta")
        t.add_column("Property", style="cyan")
        t.add_column("Value", style="green")

        t.add_row(
            "Active fishermen",
            f"{len(self.agent.active_fishermen)}/{self.agent.fisherman_limit}",
        )
        t.add_row(
            "Fishes taken today",
            f"{self.agent.fishes_taken_count}/{self.agent.fish_takes_limit}",
        )

        console.print(t)

    def show_fishermen(self):
        if not self.agent.active_fishermen:
            console.print("[dim]No active fishermen.[/dim]")
            return

        t = Table(title="Active Fishermen", show_header=True, header_style="bold blue")
        t.add_column("#", style="cyan", width=3)
        t.add_column("JID", style="green")

        for i, jid in enumerate(sorted(self.agent.active_fishermen), 1):
            t.add_row(str(i), jid)

        console.print(t)


class OwnerAgent(Agent):

    def __init__(self, jid, password, water_caretaker_jid, fish_caretaker_jid):
        super().__init__(jid, password)

        self.water_caretaker_jid = water_caretaker_jid
        self.fish_caretaker_jid = fish_caretaker_jid

        # Track active fishermen by JID to prevent double-counting
        self.active_fishermen = set()  # Set of JIDs currently in the fishery
        self.fisherman_limit = 10  # Maximum number of fishermen
        self.fishes_taken_count = 0
        self.fish_takes_limit = 50  # Daily limit for fish takes

        self.pending_stocking_prompt = asyncio.Event()
        self.last_stocking_alarm = None

    def check_if_entrance_possible(self, fisherman_jid):
        """
        Check if entrance is possible based on current fisherman count.
        Also checks if this fisherman is already in the fishery.

        Args:
            fisherman_jid: JID of the fisherman requesting entrance

        Returns:
            tuple: (allowed: bool, reason: str)
        """
        # Check if fisherman is already in the fishery
        if fisherman_jid in self.active_fishermen:
            return False, "You are already in the fishery."

        # Check if fishery is at capacity
        if len(self.active_fishermen) >= self.fisherman_limit:
            return False, f"Fishery is at capacity ({self.fisherman_limit} fishermen)."

        return True, "Entrance allowed."

    def check_if_can_take_fish(self):
        """Check if fisherman can take fish based on daily limit"""
        return self.fishes_taken_count < self.fish_takes_limit

    def get_fisherman_count(self):
        """Get current number of active fishermen"""
        return len(self.active_fishermen)

    def recommend_stocking(self):
        """Recommend stocking for end user"""
        logger.info("Restocking needed")

    def setup_stocking_alarm(self):
        t = Template(
            to=self.jid,
            sender=self.fish_caretaker_jid,
            metadata={
                "protocol": Protocols.SEND_NEEDS_STOCKING_ALARM.value,
                "performative": "request",
                "language": "JSON",
            },
        )
        b = self.ReceiveNeedsStockingAlarmBehaviour()
        self.add_behaviour(b, t)

    def register_stocking(self):
        # @TODO Add this to owner GUI
        pass

    class ReceiveNeedsStockingAlarmBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=30)
            if not msg:
                return

            logger.warning(f"NEEDS STOCKING alarm received: {msg.body}")

            # zapisz payload (jeśli JSON – można sparsować)
            try:
                self.agent.last_stocking_alarm = (
                    json.loads(msg.body) if msg.body else {}
                )
            except Exception:
                self.agent.last_stocking_alarm = {"raw": msg.body}

            # ustaw flagę dla GUI
            self.agent.pending_stocking_prompt.set()

    class HandleIfCanEnterRequestBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=30)
            if msg:
                conversation_id = msg.metadata.get("conversation-id")
                in_reply_to = msg.metadata.get("reply-with")
                fisherman_jid = str(msg.sender)

                logger.info(
                    f"Received entrance request from {fisherman_jid}: '{msg.body}'"
                )

                allow, reason = self.agent.check_if_entrance_possible(fisherman_jid)

                reply = msg.make_reply()
                reply.metadata["protocol"] = Protocols.IF_CAN_ENTER_RESPONSE.value
                reply.metadata["language"] = "JSON"
                reply.metadata["in-reply-to"] = in_reply_to
                reply.metadata["conversation-id"] = conversation_id
                reply.metadata["reply-with"] = str(uuid())

                try:
                    if allow:
                        # Add fisherman to active set
                        self.agent.active_fishermen.add(fisherman_jid)
                        reply.body = json.dumps({"allow": True, "reason": ""})
                        reply.metadata["performative"] = "agree"
                        logger.info(
                            f"Sending entrance approval to {fisherman_jid}. Current fishermen: {self.agent.get_fisherman_count()}/{self.agent.fisherman_limit}"
                        )
                    else:
                        reply.body = json.dumps({"allow": False, "reason": reason})
                        reply.metadata["performative"] = "refuse"

                        logger.warning(
                            f"Sending entrance denial to {fisherman_jid}. Reason: {reason}. Current: {self.agent.get_fisherman_count()}/{self.agent.fisherman_limit}"
                        )
                    await self.send(reply)
                except json.JSONDecodeError as e:
                    logger.error(
                        f"Exception while sending if_can_enter response message. Reason: {e}"
                    )

    class HandleIfCanTakeFishBehaviour(CyclicBehaviour):
        """Handle requests for permission to take fish (if_can_take_fish_request)"""

        async def run(self):
            msg = await self.receive(timeout=30)
            if msg:
                try:
                    in_reply_to = msg.metadata.get("reply-with")
                    conversation_id = msg.metadata.get("conversation-id")
                    fish_data = json.loads(msg.body)
                    species = fish_data.get("species", "Unknown")
                    size = fish_data.get("size", "Unknown")
                    mass = fish_data.get("mass", 0)

                    logger.info(
                        f"Received take fish permission request from {msg.sender}: {species} ({size}, {mass}kg)"
                    )

                    can_take = self.agent.check_if_can_take_fish()

                    reply = msg.make_reply()
                    reply.metadata["protocol"] = (
                        Protocols.IF_CAN_TAKE_FISH_RESPONSE.value
                    )
                    reply.metadata["language"] = "JSON"
                    reply.metadata["reply-with"] = str(uuid())
                    reply.metadata["conversation-id"] = conversation_id
                    reply.metadata["in-reply-to"] = in_reply_to

                    if can_take:
                        reply.body = json.dumps(
                            {
                                "allow": True,
                                "message": "You can take this fish.",
                            }
                        )
                        reply.metadata["performative"] = "agree"
                        self.agent.fishes_taken_count += 1
                        logger.info(
                            f"Permission granted. Fishes taken today: {self.agent.fishes_taken_count}/{self.agent.fish_takes_limit}"
                        )
                    else:
                        reply.body = json.dumps(
                            {
                                "allow": False,
                                "message": "Daily fish take limit exceeded.",
                            }
                        )
                        reply.metadata["performative"] = "refuse"
                        logger.warning(
                            f"Permission denied. Daily limit reached: {self.agent.fishes_taken_count}/{self.agent.fish_takes_limit}"
                        )

                    await self.send(reply)
                except json.JSONDecodeError:
                    logger.error("Error parsing fish data from message")

    class HandleExitRegistrationBehaviour(CyclicBehaviour):
        """Handle exit registration from fishermen (register_exit_request)"""

        async def run(self):
            msg = await self.receive(timeout=30)
            if msg:
                try:
                    in_reply_to = msg.metadata.get("reply-with")
                    conversation_id = msg.metadata.get("conversation-id")
                    exit_data = json.loads(msg.body)
                    fisherman = exit_data.get("fisherman", "Unknown")
                    fishes_taken = exit_data.get("fishes_taken", 0)
                    exit_time = exit_data.get("exit_time", "")

                    fisherman_jid = str(msg.sender)
                    logger.info(
                        f"Received exit registration from {fisherman_jid}: fisherman={fisherman}, fishes_taken={fishes_taken}, exit_time={exit_time}"
                    )

                    # Remove fisherman from active set
                    if fisherman_jid in self.agent.active_fishermen:
                        self.agent.active_fishermen.remove(fisherman_jid)
                        logger.info(f"Removed {fisherman_jid} from active fishermen")
                    else:
                        logger.warning(
                            f"Exit registration from {fisherman_jid} who was not in active fishermen list"
                        )

                    # Acknowledge exit
                    reply = msg.make_reply()
                    reply.metadata["protocol"] = Protocols.REGISTER_EXIT_RESPONSE.value
                    reply.metadata["language"] = "JSON"
                    reply.metadata["reply-with"] == str(uuid())
                    reply.metadata["conversation-id"] = conversation_id
                    reply.metadata["in-reply-to"] = in_reply_to
                    reply.body = json.dumps(
                        {
                            "status": "acknowledged",
                            "message": "Exit registered successfully.",
                        }
                    )
                    reply.metadata["performative"] = "inform"

                    logger.info(
                        f"Exit acknowledged. Current fishermen on fishery: {self.agent.get_fisherman_count()}/{self.agent.fisherman_limit}"
                    )

                    await self.send(reply)
                except json.JSONDecodeError:
                    logger.error("Error parsing exit data from message")

    class ReceiveWaterQualityAlarmBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive()
            if msg:
                logger.warning(f"Water alarm received: [{msg.sender}] {msg.body}")

    async def setup(self):
        logger.info(f"Agent {self.jid} starting")

        self.setup_if_can_enter()
        self.setup_take_fish_permission()
        self.setup_exit_registration()
        self.setup_water_alarm()
        self.setup_stocking_alarm()

        self.add_behaviour(OwnerUserGUI())

    def setup_if_can_enter(self):
        fisher_template = Template(
            to=self.jid,
            metadata={
                "protocol": Protocols.IF_CAN_ENTER_REQUEST.value,
                "performative": "query_if",
                "language": "JSON",
            },
        )

        handle_request_behaviour = self.HandleIfCanEnterRequestBehaviour()
        self.add_behaviour(handle_request_behaviour, fisher_template)

    def setup_take_fish_permission(self):
        """Setup handler for take fish permission requests"""
        take_fish_template = Template(
            to=self.jid,
            metadata={
                "protocol": Protocols.IF_CAN_TAKE_FISH_REQUEST.value,
                "performative": "query_if",
                "language": "JSON",
            },
        )

        take_fish_behaviour = self.HandleIfCanTakeFishBehaviour()
        self.add_behaviour(take_fish_behaviour, take_fish_template)

    def setup_exit_registration(self):
        """Setup handler for exit registration"""
        exit_template = Template(
            to=self.jid,
            metadata={
                "protocol": Protocols.REGISTER_EXIT_REQUEST.value,
                "performative": "inform",
                "language": "JSON",
            },
        )

        exit_behaviour = self.HandleExitRegistrationBehaviour()
        self.add_behaviour(exit_behaviour, exit_template)

    def setup_water_alarm(self):
        water_alarm_template = Template(
            to=self.jid,
            sender=self.water_caretaker_jid,
            metadata={
                "protocol": Protocols.SEND_WATER_QUALITY_ALARM.value,
                "performative": "request",
                "language": "JSON",
            },
        )
        water_alarm_behaviour = self.ReceiveWaterQualityAlarmBehaviour()

        self.add_behaviour(water_alarm_behaviour, water_alarm_template)
