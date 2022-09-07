import textwrap
from pathlib import Path
from typing import Optional, List, Union, Tuple

from expkit.base.utils.base import error_on_fail
from expkit.base.utils.type_checking import type_guard, check_type

CMD_ARGS_NONE = ""
CMD_ARGS_ONE = "1"
CMD_ARGS_MANY = "*"
CMD_ARG_MORE_THAN_ONE = "+"


class CommandOptions():

    def __init__(self, config: Optional[dict], artifacts: Optional[List[str]], output_directory: Optional[Path], num_threads: int):
        self.config = config
        self.artifacts = artifacts
        self.output_directory = output_directory
        self.num_threads = num_threads


class CommandTemplate:
    @type_guard
    def __init__(self, name: str, parameters: Union[str, int], description: str):
        self.name = name
        self.description = description
        parameters = str(parameters)
        self.parameters = parameters

        self.children = []

        if not (parameters.isnumeric() or
                parameters == CMD_ARGS_NONE or
                parameters == CMD_ARGS_ONE or
                parameters == CMD_ARGS_MANY or
                parameters == CMD_ARG_MORE_THAN_ONE):
            raise ValueError(f"Invalid numer of parameters: {parameters}")

    def _execute_command(self, options: CommandOptions, *args) -> bool:
        """Execute the command. Return False to show help."""
        raise NotImplementedError("Not implemented")

    def get_child_command(self, name: str) -> Optional["CommandTemplate"]:
        for child in self.children:
            if child.get_real_name() == name:
                return child
        return None

    def execute(self, options: CommandOptions, *args) -> bool:
        error_on_fail(check_type(args, Tuple[str]), "Invalid arguments")

        m = self.get_command(*args)
        if m is None:
            return False

        return m[0]._execute_command(options, *m[1])

    def add_child_command(self, child: "CommandTemplate"):
        if len(child.name) <= 1:
            raise ValueError("Invalid command name")
        if child.name in [c.name for c in self.children]:
            raise ValueError(f"Command {child.name} already exists")
        if not child.name.startswith(self.name):
            raise ValueError(f"Command {child.name} must be a direct child of {self.name}")
        if child.name[len(self.name)] != "." and "." not in child.name[len(self.name)+1:]:
            raise ValueError(f"Command {child.name} must be a direct child of {self.name}")

        self.children.append(child)

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
        if not child.name.startswith(self.name):
            return False
        if child.name[len(self.name)] != "." and "." not in child.name[len(self.name)+1:]:
            return False
        return True

    def get_command(self, *args) -> Optional[Tuple["CommandTemplate", Tuple[any]]]:
        error_on_fail(check_type(args, Tuple[str]), "Invalid arguments")

        # Get child commands fist
        if len(args) > 0:
            sub_name = args[0]
            cmd = self.get_child_command(sub_name)
            if cmd is not None:
                return cmd.get_command(*args[1:])

        # Else check if this command is working
        if self.parameters.isnumeric():
            num = int(self.parameters)
            if len(args) == num:
                return self, args
        elif self.parameters == CMD_ARGS_NONE:
            if len(args) == 0:
                return self, args
        elif self.parameters == CMD_ARGS_ONE:
            if len(args) == 1:
                return self, args
        elif self.parameters == CMD_ARGS_MANY:
            if len(args) >= 0:
                return self, args
        elif self.parameters == CMD_ARG_MORE_THAN_ONE:
            if len(args) > 1:
                return self, args

        return None

    def __len__(self):
        return len(self.get_children(True)) + 1

    def finalize(self):
        # Called when auto discover of commands in done
        pass

    def get_pretty_description_header(self) -> str:
        return f"{self.get_real_name()}"

    def get_pretty_description(self, indent: int = 2, max_width: int = 80) -> str:
        return textwrap.fill(f"{self.get_pretty_description_header()}\n{self.description}", max_width, subsequent_indent=" " * indent)
