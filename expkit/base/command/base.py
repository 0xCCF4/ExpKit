import argparse
import hashlib
import os
import sys
import tempfile
import textwrap
import bisect
from pathlib import Path
from typing import Optional, List, Tuple, Type, TypeVar

from expkit.base.logger import get_logger
from expkit.base.utils.base import error_on_fail
from expkit.base.utils.type_checking import type_guard, check_type


LOGGER = get_logger(__name__)


class CommandOptions:
    def __init__(self):
        self.config_file: Optional[Path] = None
        self.output_directory: Optional[Path] = None
        self.temp_directory: Optional[Path] = None
        self.log_verbose: bool = False
        self.log_debug: bool = False
        self.log_file: Optional[Path] = None


U = TypeVar('U', bound=CommandOptions)


class CommandTemplate:
    #@type_guard
    def __init__(self, name: str, description_short: str, description_long: Optional[str] = None, options: Type[U] = CommandOptions):
        self.name = name
        self.description_short = description_short
        self.description_long = description_long
        self.options_type = options

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
        cols = 80
        try:
            cols = os.get_terminal_size().columns
        except OSError:
            LOGGER.info("Cannot get terminal size, using default 80 columns")
        parser = argparse.ArgumentParser(description=f"Exploit/Payload building framework\n\n{self.get_pretty_description(short_description=False, max_width=cols)}", formatter_class=argparse.RawTextHelpFormatter, add_help=False)
        group = parser.add_argument_group("Standard options")

        group.add_argument("-h", "--help", action="store_true", default=False, help="Show this help message and exit")

        group.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output", default=False)
        group.add_argument("-d", "--debug", action="store_true", help="Enable debug output", default=False)
        #group.add_argument("-c", "--config", help="Specify configuration file to load", type=str, default=None)
        #group.add_argument("-o", "--output", help="Build output directory", type=str, default=None)
        #group.add_argument("-t", "--temp-dir", help="Temporary build directory", type=str, default=None)
        group.add_argument("-l", "--log", help="Log file", type=str, default=None)

        return parser

    def parse_arguments(self, *args: str, parser: Optional[argparse.ArgumentParser]) -> Tuple[U, argparse.ArgumentParser, argparse.Namespace]:
        if parser is None:
            parser = self.create_argparse()

        args = parser.parse_args(args)

        options = self.options_type()

        # Parse arguments

        if args.debug:
            options.log_debug = True
            options.log_verbose = True

        if args.verbose:
            options.log_verbose = True

        if args.log is not None:
            options.log_file = Path(args.log)

        if hasattr(args, "config") and args.config is not None:
            options.config_file = Path(args.config)

        if hasattr(args, "output") and args.output is not None:
            options.output_directory = Path(args.output)

        if hasattr(args, "temp_dir") and args.temp_dir is not None:
            options.temp_directory = Path(args.temp_dir)

        if args.help:
            parser.print_help()
            sys.exit(0)

        # Validate arguments

        if options.config_file is None:
            options.config_file = Path("config.json")

        if options.config_file is not None:
            if not options.config_file.exists():
                raise ValueError(f"Configuration file {options.config_file} does not exist")
            if not options.config_file.is_file():
                raise ValueError(f"Configuration file {options.config_file} is not a file")

        if options.output_directory is not None:
            if not options.output_directory.exists():
                options.output_directory.mkdir(parents=True)
            else:
                LOGGER.warning(f"Output directory '{options.output_directory.absolute()}' already exists, files may be overwritten")

        if options.output_directory is None:
            options.output_directory = Path("build")
            if not options.output_directory.exists():
                options.output_directory.mkdir(parents=True)
            else:
                LOGGER.warning(f"Output directory '{options.output_directory.absolute()}' already exists, files may be overwritten")

        if options.temp_directory is not None:
            pass

        if options.temp_directory is None:
            options.temp_directory = Path(tempfile.gettempdir()) / "expkit-tmp"

        if options.config_file is not None:
            hash_path = hashlib.sha512(str(options.config_file.absolute()).encode("utf-8"))
            options.temp_directory = options.temp_directory / hash_path.hexdigest()[:24]
        else:
            options.temp_directory = options.temp_directory / "default"

        if not options.temp_directory.exists():
            options.temp_directory.mkdir(parents=True)

        return options, parser, args

    # For bisect.insort_left
    def __lt__(self, other):
        return self.get_real_name() < other.get_real_name()

