import textwrap
import bisect
from pathlib import Path
from typing import Optional, List, Union, Tuple

from expkit.base.utils.base import error_on_fail
from expkit.base.utils.type_checking import type_guard, check_type


class CommandArgumentCount:
    __slots__ = ("min", "max")

    def __init__(self, min: int, max: Union[int, str, type(None)] = None):
        if max is None:
            max = min

        if isinstance(max, str) and max != "*":
            raise ValueError(f"Invalid argument count string: {max}")

        self.min = min
        self.max = max if not str(max).isnumeric() else int(max)

        assert not str(max).isnumeric() or isinstance(self.max, int)

    def __repr__(self):
        return f"CommandArgumentCount(min={self.min}, max={self.max})"

    def __eq__(self, other):
        if not isinstance(other, CommandArgumentCount):
            return False

        return self.min == other.min and self.max == other.max

    def matched(self, argument_count: int) -> bool:
        if isinstance(self.max, int):
            return self.min <= argument_count <= self.max
        elif self.max == "*":
            return self.min <= argument_count
        else:
            raise RuntimeError(f"Invalid argument count: {self.max}")


class CommandOptions:

    def __init__(self, config: Optional[dict], artifacts: Optional[List[str]], output_directory: Optional[Path], num_threads: int, verbose: bool):
        self.config = config
        self.artifacts = artifacts
        self.output_directory = output_directory
        self.num_threads = num_threads
        self.verbose = verbose


class CommandTemplate:
    @type_guard
    def __init__(self, name: str, argument_count: CommandArgumentCount, description_short: str, description_long: Optional[str] = None):
        self.name = name
        self.description_short = description_short
        self.description_long = description_long
        self.argument_count = argument_count

        self.children = []
        self.parent: Optional[CommandTemplate] = None

    def _execute_command(self, options: CommandOptions, *args) -> bool:
        """Execute the command. Return False to show help."""
        raise NotImplementedError("Not implemented")

    def get_child_command(self, name: str) -> Optional["CommandTemplate"]:
        for child in self.children:
            if child.get_real_name() == name:
                return child
        return None

    def execute(self, options: CommandOptions, *args) -> bool:
        error_on_fail(check_type(list(args), List[str]), "Invalid arguments")

        return self._execute_command(options, *args)

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

        # Else check if this command is working
        if self.argument_count.matched(len(args)):
            return self, args

        return None

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

    # For bisect.insort_left
    def __lt__(self, other):
        return self.get_real_name() < other.get_real_name()

