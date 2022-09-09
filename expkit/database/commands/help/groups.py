import textwrap
from typing import Optional, get_type_hints

from expkit.base.command.base import CommandTemplate, CommandOptions, CommandArgumentCount
from expkit.base.logger import get_logger
from expkit.framework.database import register_command, StageDatabase, GroupDatabase

LOGGER = get_logger(__name__)
PRINT = get_logger(__name__, True)


@register_command
class GroupInfoCommand(CommandTemplate):
    def __init__(self):
        super().__init__(".help.groups", CommandArgumentCount(0, "*"), textwrap.dedent('''\
            Print information about groups.
        '''), textwrap.dedent('''\
            Print information about a specific group. If no name is given, a list
            of all groups, is printed.
            When a name is given, the help for the specific group is printed.
            This includes a description and a list of available config parameters.
            '''))

    def _execute_command(self, options: CommandOptions, *args) -> bool:
        db = GroupDatabase.get_instance()

        if len(args) == 1 and args[0] == "all":
            args = tuple([s.name for s in db.groups.values()])

        if len(args) == 0:
            PRINT.info(f"Printing list of all groups")
            for stage in db.groups.values():
                PRINT.info(f" - {stage.name}")
            PRINT.info("")
        else:
            for name in args:
                group = db.get_group(name)
                if group is None:
                    LOGGER.error(f"Group not found: {name}")
                else:
                    PRINT.info(f"Group '{name}'")
                    PRINT.info(textwrap.fill(f"Description: {group.description}", initial_indent='  ', subsequent_indent='    '))

                    PRINT.info(f"  Supported platforms:")
                    for entry in group.get_supported_platforms():
                        PRINT.info(f"    - {entry.platform.name} ({entry.architecture.name}) | {entry.input_type} ({entry.dependencies}) -> {entry.output_type}")

                    if len(group.stages) > 0:
                        PRINT.info(f"  Stages:")
                        for stage in group.stages:
                            PRINT.info(f"    - {stage}")

                    PRINT.info(f"")


        return True

    def get_pretty_description_header(self) -> str:
        return f"{super().get_pretty_description_header()} [name]"

