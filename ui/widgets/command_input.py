from textual.widgets import Input
from textual.message import Message
from typing import Callable, Awaitable, Optional


class CommandInput(Input):
    """
    Simple command input widget.
    
    Features:
    - Sends input to async handler on Enter
    - Minimal, clean, works with CommandManager
    """

    def __init__(
        self,
        command_handler: Optional[Callable[[str], Awaitable[tuple[str, bool]]]] = None,
        placeholder: str = "Enter command...",
        **kwargs
    ):
        super().__init__(placeholder=placeholder, **kwargs)
        self.command_handler = command_handler

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """
        Called when Enter is pressed in the input.
        Passes command to handler and clears the input.
        """
        command = event.value.strip()
        if not command:
            return

        # Call the handler if provided
        if self.command_handler:
            try:
                message, success = await self.command_handler(command)
                # Optionally, you can print/log or notify the app
                # print(f"[{'OK' if success else 'ERR'}] {message}")
            except Exception as e:
                # Log or notify error
                print(f"Command handler error: {e}")

        # Clear the input after submission
        self.value = ""

    class CommandSubmitted(Message):
        """Message sent when command is submitted."""
        def __init__(self, command: str):
            super().__init__()
            self.command = command
