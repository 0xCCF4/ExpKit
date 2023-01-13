import argparse
import textwrap
from typing import Optional, List, Tuple

from expkit.base.command.base import CommandTemplate, CommandOptions
from expkit.base.logger import get_logger
from expkit.framework.database import register_command


LOGGER = get_logger(__name__)
PRINT = get_logger(__name__, True)


class HelpOptions(CommandOptions):
    def __init__(self):
        super().__init__()
        self.help_command: List[str] = []


@register_command
class HelpCommand(CommandTemplate):
    def __init__(self):
        super().__init__(".help.cmd", textwrap.dedent('''\
            Print help about a command.
            '''), options=HelpOptions)

        self._root_cmd: Optional[CommandTemplate] = None

    def create_argparse(self) -> argparse.ArgumentParser:
        parser = super().create_argparse()
        group = parser.add_argument_group("Help Options")

        group.add_argument("cmd", help="Print help about command cmd", type=str, nargs="*")

        return parser

    def parse_arguments(self, *args: str) -> Tuple[HelpOptions, argparse.ArgumentParser, argparse.Namespace]:
        options, parser, args = super().parse_arguments(*args)

        options.help_command = args.cmd

        return options, parser, args

    def execute(self, options: HelpOptions) -> bool:
        assert self._root_cmd is not None

        PRINT.info(f"\nPrinting help about command '{' '.join(options.help_command)}'\n")

        if len(options.help_command) == 0:
            PRINT.info(f"{self.get_pretty_description()}\n")
            LOGGER.warning(f"No command name given.")
        else:
            m = self._root_cmd.get_command(*options.help_command)
            if m is None:
                LOGGER.error(f"Command not found: {' '.join(options.help_command)}")
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
