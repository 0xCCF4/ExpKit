import argparse
import os
import textwrap
import bisect
from pathlib import Path
from typing import Optional, List, Union, Tuple

from expkit.base.logger import get_logger
from expkit.base.utils.base import error_on_fail
from expkit.base.utils.type_checking import type_guard, check_type


LOGGER = get_logger(__name__)


class CommandOptions:
    def __init__(self):
        self.config_file: Optional[Path] = None
        self.output_directory: Optional[Path] = None
        self.working_directory: Optional[Path] = None
        self.temp_directory: Optional[Path] = None
        self.log_verbose: bool = False
        self.log_debug: bool = False
        self.log_file: Optional[Path] = None


class CommandTemplate:
    #@type_guard
    def __init__(self, name: str, description_short: str, description_long: Optional[str] = None):
        self.name = name
        self.description_short = description_short
        self.description_long = description_long

        self.children = []
        self.parent: Optional[CommandTemplate] = None

    def get_child_command(self, name: str) -> Optional["CommandTemplate"]:
        for child in self.children:
            if child.get_real_name() == name:
                return child
        return None

    def execute(self, options: CommandOptions) -> bool:
        """Execute the command. Return False to show help."""
        raise NotImplementedError("Not implemented")

    def add_command(self, child: "CommandTemplate"):
        if len(child.name) <= 1:
            raise ValueError("Invalid command name")
        if child.name in [c.name for c in self.children]:
            raise ValueError(f"Command {child.name} already exists")
        if not child.name.startswith(self.name) or child.name == self.name:
            raise ValueError(f"Command {child.name} must be a direct child of {self.name}")
        if child.name[len(self.name)] != "." or "." in child.name[len(self.name)+1:]:
            raise ValueError(f"Command {child.name} must be a direct child of {self.name}")
        if child.parent is not None:
            raise ValueError(f"Command {child.name} is already attached to {child.parent.name}")

        child.parent = self
        bisect.insort_left(self.children, child)

    def get_real_name(self):
        return self.name.split(".")[-1]

    def get_children(self, recursive: bool=False, order_child_first=True) -> List["CommandTemplate"]:
        commands = []
        for child in self.children:
            if order_child_first:
                commands.append(child)
            if recursive:
                commands.extend(child.get_children(recursive, order_child_first))
            if not order_child_first:
                commands.append(child)
        return commands

    def can_be_attached_as_child(self, child: "CommandTemplate") -> bool:
        if len(child.name) <= 1:
            return False
        if not child.name.startswith(self.name) or child.name == self.name:
            return False
        if child.name[len(self.name)] != "." or "." in child.name[len(self.name)+1:]:
            return False
        return True

    def get_command(self, *args) -> Optional[Tuple["CommandTemplate", tuple]]:
        error_on_fail(check_type(list(args), List[str]), "Invalid arguments")

        # Get child commands fist
        if len(args) > 0:
            sub_name = args[0]
            cmd = self.get_child_command(sub_name)
            if cmd is not None:
                return cmd.get_command(*args[1:])

        return self, args

    def __len__(self):
        return len(self.get_children(True)) + 1

    def finalize(self):
        # Called when auto discover of commands in done
        pass

    def get_pretty_description_header(self) -> str:
        return f"{' '.join(self.name[1:].split('.'))}"

    def get_pretty_description(self, indent: int = 4, max_width: int = 80, short_description: bool = True) -> str:
        text = self.description_short if short_description else self.description_long
        if text is None and not short_description:
            text = self.description_short
        if text is None:
            text = "<no description provided>"
        return f"{self.get_pretty_description_header()}\n{textwrap.fill(text, max_width, initial_indent=' ' * indent, subsequent_indent=' ' * indent)}"

    def create_argparse(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(description=self.get_pretty_description())
        base_group = parser.add_argument_group("Standard options")

        base_group.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output", default=False)
        base_group.add_argument("-d", "--debug", action="store_true", help="Enable debug output", default=False)
        base_group.add_argument("-c", "--config", help="Specify configuration file to load", type=str, default=None)
        base_group.add_argument("-o", "--output", help="Build output directory", type=str, default=None)
        base_group.add_argument("-t", "--temp-dir", help="Temporary build directory", type=str, default=None)
        base_group.add_argument("-w", "--working-dir", help="Working directory", type=str, default=None)
        base_group.add_argument("-l", "--log", help="Log file", type=str, default=None)

        return parser

    def parse_arguments(self, *args: str) -> Tuple[CommandOptions, argparse.ArgumentParser]:
        parser = self.create_argparse()

        args = parser.parse_args(args)

        options = CommandOptions()

        # Parse arguments

        if args.debug:
            options.log_debug = True
            options.log_verbose = True

        if args.verbose:
            options.log_verbose = True

        if args.log is not None:
            options.log_file = Path(args.log)

        if args.config is not None:
            options.config_file = Path(args.config)

        if args.output is not None:
            options.output_directory = Path(args.output)

        if args.temp_dir is not None:
            options.temp_directory = Path(args.temp_dir)

        if args.working_dir is not None:
            options.working_directory = Path(args.working_dir)

        # Validate arguments

        if options.config_file is not None:
            if not options.config_file.exists():
                raise ValueError(f"Configuration file {options.config_file} does not exist")
            if not options.config_file.is_file():
                raise ValueError(f"Configuration file {options.config_file} is not a file")

        if options.working_directory is not None:
            if not options.working_directory.exists():
                raise ValueError(f"Working directory {options.working_directory} does not exist")
            if not options.working_directory.is_dir():
                raise ValueError(f"Working directory {options.working_directory} is not a directory")

        if options.output_directory is not None:
            # todo
            pass

        if options.temp_directory is not None:
            # todo
            pass

        if options.temp_directory is None:
            # todo Path(tempfile.mkdtemp(prefix="expkit_", suffix="_build"))
            pass

        return options, parser


    # For bisect.insort_left
    def __lt__(self, other):
        return self.get_real_name() < other.get_real_name()

