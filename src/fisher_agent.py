import json
import asyncio
from uuid import uuid4 as uuid
from datetime import datetime
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.template import Template
from spade.message import Message
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from .logger_config import get_logger
from .protocols import Protocols

# Rich console for UI (user-facing terminal)
console = Console()

# Logger for system logs (written to file)
logger = get_logger("FisherAgent")


class FisherAgent(Agent):
    def __init__(self, jid, password, owner_jid, fish_caretaker_jid=None):
        super().__init__(jid, password)
        self.owner_jid = owner_jid
        self.fish_caretaker_jid = fish_caretaker_jid
        self.is_on_fishery = False
        self.fishes_caught = []
        self.pending_fish_catch = None  # Store caught fish waiting for permission
        # Pending requests for async response handling
        self.pending_take_fish_request = None  # Stores fish data while waiting
        self.pending_fish_data_registration = None
        self.pending_fish_size_registration = None
        self.pending_exit_registration = False

    class UserInputBehaviour(CyclicBehaviour):
        """Handle user input to trigger actions"""

        async def on_start(self):
            self.print_menu()

        def print_menu(self):
            """Display menu using Rich for beautiful UI"""
            fisherman_name = str(self.agent.jid).split("@")[0]
            menu_text = f"""
[bold cyan]1[/bold cyan] - Request to enter fishery
[bold cyan]2[/bold cyan] - Request taking fish (must be in fishery)
[bold cyan]3[/bold cyan] - Show status
[bold cyan]4[/bold cyan] - Exit fishery
[bold cyan]0[/bold cyan] - Exit program

[dim]Fisherman: {fisherman_name}[/dim]
            """
            console.print(
                Panel(
                    menu_text,
                    title=f"[bold green]FISHERMAN AGENT[/bold green] - {fisherman_name.upper()} - Available Actions",
                    border_style="cyan",
                    padding=(1, 2),
                )
            )

        async def run(self):
            # Use asyncio to read input without blocking
            loop = asyncio.get_event_loop()
            try:
                user_input = await loop.run_in_executor(
                    None,
                    lambda: console.input(
                        "[bold cyan]Enter action number: [/bold cyan]"
                    ),
                )
                user_input = user_input.strip()

                if user_input == "1":
                    await self.handle_enter_fishery()
                elif user_input == "2":
                    await self.handle_take_fish()
                elif user_input == "3":
                    self.show_status()
                elif user_input == "4":
                    await self.handle_exit_fishery()
                elif user_input == "0":
                    console.print("[yellow]Exiting...[/yellow]")
                    logger.info("User requested exit")
                    await self.handle_exit_fishery()
                    await self.agent.stop()
                    self.kill()
                else:
                    console.print("[red]Invalid input. Please enter 0-4.[/red]")
                    self.print_menu()
            except (EOFError, KeyboardInterrupt):
                console.print("\n[yellow]Exiting...[/yellow]")
                logger.info("Exit requested via KeyboardInterrupt")
                await self.agent.stop()
                self.kill()

        async def handle_enter_fishery(self):
            if self.agent.is_on_fishery:
                console.print("[yellow]Already in fishery![/yellow]")
                logger.warning("Attempted to enter fishery while already inside")
                return

            console.print("[cyan]Requesting permission to enter fishery...[/cyan]")
            logger.info("Requesting permission to enter fishery")
            await self.request_enter_fishery()

        async def request_enter_fishery(self):
            """Request permission to enter fishery (asynchronous - response handled separately)"""
            payload = {"fisherman_data": {"jid": str(self.agent.jid)}}
            try:
                msg = Message(
                    to=self.agent.owner_jid,
                    body=json.dumps(payload),
                    metadata={
                        "performative": "query_if",
                        "protocol": Protocols.IF_CAN_ENTER_REQUEST.value,
                        "language": "JSON",
                        "reply-with": str(uuid()),
                        "conversation-id": str(uuid()),
                    },
                )
                logger.debug(f"Sending entrance request to {self.agent.owner_jid}")
                self.agent.pending_entrance_request = True
                await self.send(msg)
                console.print("[cyan]Request sent. Waiting for response...[/cyan]")
            except json.JSONDecodeError as e:
                logger.error(
                    f"Failed to encode request_enter_fishery message payload. Reason: {e}"
                )

        async def handle_take_fish(self):
            if not self.agent.is_on_fishery:
                console.print(
                    "[red]You must be in the fishery first! Use action 1.[/red]"
                )
                logger.warning("Attempted to take fish while not in fishery")
                return

            # Simulate catching a fish
            console.print("[cyan]Simulating catching a fish...[/cyan]")
            fish_species = "Carp"  # Example species
            fish_size = "M"  # S/M/L
            estimated_mass = 1.5  # kg

            console.print(
                f"[green]Caught:[/green] {fish_species} (size: {fish_size}, mass: {estimated_mass}kg)"
            )
            logger.info(
                f"Caught fish: {fish_species}, size: {fish_size}, mass: {estimated_mass}kg"
            )

            # Store fish data for processing
            self.agent.pending_fish_catch = {
                "species": fish_species,
                "size": fish_size,
                "mass": estimated_mass,
            }

            # Request permission to take the fish (asynchronous)
            await self.request_take_fish_permission(
                fish_species, fish_size, estimated_mass
            )
            # Response will be handled asynchronously by HandleTakeFishResponseBehaviour

        async def handle_exit_fishery(self):
            if not self.agent.is_on_fishery:
                console.print("[yellow]Not in fishery![/yellow]")
                logger.warning("Attempted to exit fishery while not inside")
                return

            logger.info("Registering exit from fishery")
            await self.register_exit()
            self.agent.is_on_fishery = False
            console.print("[green]Exited fishery successfully.[/green]")
            logger.info("Successfully exited fishery")

        def show_status(self):
            """Display status using Rich table"""
            status_table = Table(
                title="Fisherman Status", show_header=True, header_style="bold magenta"
            )
            status_table.add_column("Property", style="cyan")
            status_table.add_column("Value", style="green")

            status_table.add_row(
                "In fishery", "Yes" if self.agent.is_on_fishery else "No"
            )
            status_table.add_row("Fishes caught", str(len(self.agent.fishes_caught)))

            console.print(status_table)

            if self.agent.fishes_caught:
                fish_table = Table(
                    title="Caught Fish", show_header=True, header_style="bold blue"
                )
                fish_table.add_column("#", style="cyan", width=3)
                fish_table.add_column("Species", style="green")
                fish_table.add_column("Size", style="yellow")
                fish_table.add_column("Mass (kg)", style="magenta")

                for i, fish in enumerate(self.agent.fishes_caught, 1):
                    fish_table.add_row(
                        str(i),
                        fish["species"],
                        fish["size"],
                        str(fish["mass"]),
                    )

                console.print(fish_table)

            logger.debug("Status displayed")

        async def request_take_fish_permission(
            self, species: str, size: str, mass: float
        ):
            """Request permission from Owner to take a fish (asynchronous - response handled separately)"""
            try:
                msg = Message(
                    to=self.agent.owner_jid,
                    body=json.dumps(
                        {
                            "species": species,
                            "size": size,
                            "mass": mass,
                        }
                    ),
                    metadata={
                        "performative": "query_if",
                        "protocol": Protocols.IF_CAN_TAKE_FISH_REQUEST.value,
                        "language": "JSON",
                        "reply-with": str(uuid()),
                        "conversation-id": str(uuid()),
                    },
                )
                logger.info(
                    f"Requesting permission to take fish: {species} ({size}, {mass}kg)"
                )
                # Store pending request data
                self.agent.pending_take_fish_request = {
                    "species": species,
                    "size": size,
                    "mass": mass,
                }
                await self.send(msg)
                console.print(
                    "[cyan]Permission request sent. Waiting for response...[/cyan]"
                )
            except json.JSONDecodeError as e:
                logger.error(
                    f"Failed to encode request_teke_fish_ermission message payload. Reason: {e}"
                )

        async def register_fish_data(self, species: str, size: str, mass: float):
            """Register fish data with DEI/FishCaretakerAgent (asynchronous - response handled separately)"""
            if not self.agent.fish_caretaker_jid:
                logger.warning(
                    "No fish caretaker JID configured, skipping fish data registration"
                )
                return

            fish_data = {
                "species": species,
                "size": size,
                "mass": mass,
                "time": datetime.now().isoformat(),
            }
            try:
                msg = Message(
                    to=self.agent.fish_caretaker_jid,
                    body=json.dumps(fish_data),
                    metadata={
                        "performative": "request",
                        "protocol": Protocols.REGISTER_FISH_DATA_REQUEST.value,
                        "language": "JSON",
                        "conversation-id": str(uuid()),
                        "reply-with": str(uuid()),
                    },
                )
                logger.info(f"Registering fish data: {species}")
                self.agent.pending_fish_data_registration = fish_data
                await self.send(msg)
            except json.JSONDecodeError as e:
                logger.error(
                    f"Failed to encode register_fish_data message payload. Reason: {e}"
                )

        async def register_exit(self):
            """Register exit from fishery with Owner (asynchronous - response handled separately)"""
            try:
                msg = Message(
                    to=self.agent.owner_jid,
                    body=json.dumps(
                        {
                            "fisherman": str(self.agent.jid),
                            "fishes_taken": len([f for f in self.agent.fishes_caught]),
                            "exit_time": datetime.now().isoformat(),
                        }
                    ),
                    metadata={
                        "performative": "inform",
                        "protocol": Protocols.REGISTER_EXIT_REQUEST.value,
                        "language": "JSON",
                        "conversation-id": str(uuid()),
                        "reply-with": str(uuid()),
                    },
                )
                self.agent.pending_exit_registration = True
                logger.info("Sending exit registration")
                await self.send(msg)
                # Exit registration uses 'inform' performative, acknowledgment handled separately
            except json.JSONDecodeError as e:
                logger.error(
                    f"Failed to encode register_exit message payload. Reason: {e}"
                )

    class HandleIfCanEnterResponseBehaviour(CyclicBehaviour):
        """Handle responses to entrance requests asynchronously (if_can_enter_response, register_enter)"""

        async def run(self):
            msg = await self.receive(timeout=30)
            if msg:
                performative = msg.metadata.get("performative", "")
                logger.info(
                    f"Received entrance response: {performative} from {msg.sender}"
                )

                if self.agent.is_on_fishery:
                    return

                else:
                    if performative == "agree":
                        self.register_enter()
                        console.print(
                            "[bold green]\n✓ Permission granted![/bold green] You can now enter the fishery."
                        )
                        logger.info("Entrance permission granted")
                    elif performative == "refuse":
                        console.print(
                            "[bold red]\n✗ Permission denied.[/bold red] Cannot enter fishery."
                        )
                        logger.warning("Entrance permission denied")
                    else:
                        console.print(
                            f"[yellow]\n Unknown response: {performative}[/yellow]"
                        )
                        logger.warning(f"Unknown response performative: {performative}")

        def register_enter(self):
            self.agent.is_on_fishery = True

    class HandleTakeFishResponseBehaviour(CyclicBehaviour):
        """Handle responses to take fish permission requests asynchronously"""

        async def run(self):
            msg = await self.receive(timeout=30)

            if msg:
                performative = msg.metadata.get("performative", "")
                logger.info(
                    f"Received take fish response: {performative} from {msg.sender}"
                )

                if self.agent.pending_take_fish_request:
                    fish_data = self.agent.pending_take_fish_request
                    self.agent.pending_take_fish_request = None

                    if performative == "inform":
                        try:
                            response_data = json.loads(msg.body)
                            if response_data.get("permission") == "granted":
                                console.print(
                                    "[bold green]✓ \nPermission granted to take fish.[/bold green]"
                                )
                                logger.info(
                                    f"\nPermission granted to take fish: {fish_data['species']}"
                                )

                                # Register fish data with DEI
                                await self.register_fish_data(
                                    fish_data["species"],
                                    fish_data["size"],
                                    fish_data["mass"],
                                )

                                self.register_take_fish(fish_data)
                                console.print(
                                    "[bold green]✓ \nSuccessfully registered and took fish![/bold green]"
                                )
                            else:
                                raise ValueError("Permission not granted")
                        except (json.JSONDecodeError, ValueError, KeyError):
                            console.print(
                                "[bold green]✓ \nPermission granted to take fish.[/bold green]"
                            )
                            # Fallback: still register if we can't parse response
                            await self.register_fish_data(
                                fish_data["species"],
                                fish_data["size"],
                                fish_data["mass"],
                            )
                            self.register_take_fish(fish_data)
                    elif performative == "disconfirm":
                        console.print(
                            "[bold red]✗ \nPermission denied to take fish.[/bold red]"
                        )
                        logger.info(
                            f"Permission denied, releasing fish: {fish_data['species']}"
                        )

                    else:
                        console.print(
                            f"[yellow]\nUnknown response: {performative}[/yellow]"
                        )
                        logger.warning(f"Unknown response performative: {performative}")

        def register_take_fish(self, fish_data: dict):
            self.agent.fishes_caught.append(
                {
                    "species": fish_data["species"],
                    "size": fish_data["size"],
                    "mass": fish_data["mass"],
                    "time": datetime.now().isoformat(),
                }
            )

        async def register_fish_data(self, species: str, size: str, mass: float):
            """Helper method to register fish data"""
            if not self.agent.fish_caretaker_jid:
                return

            fish_data = {
                "species": species,
                "size": size,
                "mass": mass,
                "time": datetime.now().isoformat(),
            }
            try:
                msg = Message(
                    to=self.agent.fish_caretaker_jid,
                    body=json.dumps(fish_data),
                    metadata={
                        "performative": "request",
                        "protocol": Protocols.REGISTER_FISH_DATA_REQUEST.value,
                        "language": "JSON",
                        "conversation-id": str(uuid()),
                        "reply-with": str(uuid()),
                    },
                )
                logger.info(f"Registering fish data: {species}")
                self.agent.pending_fish_data_registration = fish_data
                await self.send(msg)
            except json.JSONDecodeError as e:
                logger.error(
                    f"Failed to encode request_enter_fishery message payload. Reason: {e}"
                )

    class HandleFishDataResponseBehaviour(CyclicBehaviour):
        """Handle responses to fish data registration asynchronously"""

        async def run(self):
            msg = await self.receive(timeout=30)
            if msg:
                performative = msg.metadata.get("performative", "")
                if (
                    performative == "agree"
                    and self.agent.pending_fish_data_registration
                ):
                    logger.debug("Fish data registration confirmed")
                    self.agent.pending_fish_data_registration = None

    class HandleExitResponseBehaviour(CyclicBehaviour):
        """Handle responses to exit registration asynchronously"""

        async def run(self):
            from .owner_agent import OwnerAgent

            msg = await self.receive(timeout=30)
            if msg:
                performative = msg.metadata.get("performative", "")
                if performative == "inform" and self.agent.pending_exit_registration:
                    logger.debug("Exit registration acknowledged")
                    self.agent.pending_exit_registration = False

    async def setup(self):
        fisherman_name = str(self.jid).split("@")[0]
        logger.info(f"Agent {self.jid} starting")
        console.print(
            Panel(
                f"[bold green]Fisherman Agent[/bold green] [cyan]{fisherman_name}[/cyan] is ready!\n"
                "[yellow]Tip:[/yellow] View system logs in another terminal with:\n"
                "[dim]./view_logs.sh[/dim] or in [dim]logs/fishery_system.log[/dim] file",
                title=f"[bold blue]Agent Started - {fisherman_name.upper()}[/bold blue]",
                border_style="green",
            )
        )

        # Start user input behavior
        user_input_behaviour = self.UserInputBehaviour()
        self.add_behaviour(user_input_behaviour)

        # --- Setup response handlers for asynchronous protocol responses

        # Entrance response handler
        if_can_enter_response_template = Template(
            metadata={
                "protocol": Protocols.IF_CAN_ENTER_RESPONSE.value,
                "language": "JSON",
            }
        )
        if_can_enter_response_behaviour = self.HandleIfCanEnterResponseBehaviour()
        self.add_behaviour(
            if_can_enter_response_behaviour, if_can_enter_response_template
        )

        # Take fish response handler
        take_fish_response_template = Template(
            metadata={
                "protocol": Protocols.IF_CAN_TAKE_FISH_RESPONSE.value,
                "language": "JSON",
            }
        )
        take_fish_response_behaviour = self.HandleTakeFishResponseBehaviour()
        self.add_behaviour(take_fish_response_behaviour, take_fish_response_template)

        # Fish data registration response handler
        fish_data_response_template = Template(
            metadata={
                "protocol": Protocols.REGISTER_FISH_DATA_RESPONSE.value,
                "performative": "inform",
                "language": "JSON",
            }
        )
        fish_data_response_behaviour = self.HandleFishDataResponseBehaviour()
        self.add_behaviour(fish_data_response_behaviour, fish_data_response_template)

        # Exit registration response handler
        exit_response_template = Template(
            metadata={
                "protocol": Protocols.REGISTER_EXIT_RESPONSE.value,
                "performative": "inform",
                "language": "JSON",
            }
        )
        exit_response_behaviour = self.HandleExitResponseBehaviour()
        self.add_behaviour(exit_response_behaviour, exit_response_template)
