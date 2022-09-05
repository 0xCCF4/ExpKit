from pathlib import Path
from typing import Optional, List

from expkit.base.utils.type_checking import type_guard

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
    def __init__(self, name: str, description: str, parameters: str):
        self.name = name
        self.description = description
        self.parameters = parameters

        self.children = []

        if not (parameters.isnumeric() or
                parameters == CMD_ARGS_NONE or
                parameters == CMD_ARGS_ONE or
                parameters == CMD_ARGS_MANY or
                parameters == CMD_ARG_MORE_THAN_ONE):
            raise ValueError(f"Invalid numer of parameters: {parameters}")

    def execute(self, options: CommandOptions, cmd_name, *args) -> bool:
        """Execute the command. Return False to show help."""
        raise NotImplementedError("Not implemented")

    def add_child_command(self, child: "CommandTemplate"):
        if child.name in [c.name for c in self.children]:
            raise ValueError(f"Command {child.name} already exists")

        self.children.append(child)

    def matches(self, _, *args) -> Optional["CommandTemplate"]:
        if self.parameters.isnumeric():
            num = int(self.parameters)
            if len(args) == num:
                return self
        elif self.parameters == CMD_ARGS_NONE:
            if len(args) == 0:
                return self
        elif self.parameters == CMD_ARGS_ONE:
            if len(args) == 1:
                return self
        elif self.parameters == CMD_ARGS_MANY:
            if len(args) >= 0:
                return self
        elif self.parameters == CMD_ARG_MORE_THAN_ONE:
            if len(args) > 1:
                return self

        if len(args) > 0:
            for child in self.children:
                m = child.matches(*args)
                if m is not None:
                    return m

        return None
