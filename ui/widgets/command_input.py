from textual.widgets import Input
from textual.message import Message
from typing import Callable, Awaitable, Optional, Union
import asyncio


class CommandInput(Input):
    """
    Command input widget that integrates with CommandsManager.
    
    Features:
    - Sends input to async handler on Enter
    - Supports handlers that return None (fire-and-forget) or tuples
    - Minimal, clean, works with CommandManager
    """

    def __init__(
        self,
        command_handler: Optional[Callable[[str], Awaitable[None]]] = None,
        placeholder: str = "Enter command...",
        **kwargs
    ):
        super().__init__(placeholder=placeholder, **kwargs)
        self.command_handler = command_handler

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """
        Called when Enter is pressed in the input.
        Passes command to handler and clears the input.
        
        The handler is expected to be async and handle the command.
        It doesn't need to return anything - the CommandsManager
        handles responses via its own callback system.
        """
        command = event.value.strip()
        if not command:
            return

        # Clear the input immediately for better UX
        self.value = ""

        # Call the handler if provided
        if self.command_handler:
            try:
                # Handler is async, just await it
                # It should submit to CommandsManager which handles responses
                await self.command_handler(command)
            except Exception as e:
                # Log error - the screen should have its own error handling
                if hasattr(self.app, 'logger'):
                    self.app.logger.error(f"Command handler error: {e}")
                # Try to notify the user
                try:
                    self.app.notify(f"Command error: {str(e)}", severity="error")
                except:
                    print(f"Command handler error: {e}")

    class CommandSubmitted(Message):
        """Message sent when command is submitted."""
        def __init__(self, command: str):
            super().__init__()
            self.command = command
