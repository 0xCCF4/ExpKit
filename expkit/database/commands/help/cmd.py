import textwrap
from typing import Optional

from expkit.base.command.base import CommandTemplate, CommandOptions, CommandArgumentCount
from expkit.base.logger import get_logger
from expkit.framework.database import register_command


LOGGER = get_logger(__name__)
PRINT = get_logger(__name__, True)


@register_command
class HelpCommand(CommandTemplate):
    def __init__(self):
        super().__init__(".help.cmd", CommandArgumentCount(0, "*"), textwrap.dedent('''\
            Print help about a command.
            '''))

        self._root_cmd: Optional[CommandTemplate] = None

    def _execute_command(self, options: CommandOptions, *args) -> bool:
        assert self._root_cmd is not None

        PRINT.info(f"\nPrinting help about command '{' '.join(args)}'\n")

        if len(args) == 0:
            PRINT.info(f"{self.get_pretty_description()}\n")
            LOGGER.warning(f"No command name given.")
        else:
            m = self._root_cmd.get_command(*args)
            if m is None:
                LOGGER.error(f"Command not found: {' '.join(args)}")
            else:
                cmd, cargs = m

                PRINT.info(f"{cmd.get_pretty_description(short_description=False)}\n")
                LOGGER.debug(f"Found command: {cmd.name[1:]} with args: {cargs}")

        return True

    def get_pretty_description_header(self) -> str:
        return f"{super().get_pretty_description_header()} <command>"

    def finalize(self):
        root = self
        while root.parent is not None:
            root = root.parent

        self._root_cmd = root
