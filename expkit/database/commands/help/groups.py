import math
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
            args = tuple(sorted([s.name for s in db.groups.values()]))

        if len(args) == 0:
            PRINT.info(f"Printing list of all groups")
            for stage in sorted(db.groups.values()):
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

                    if options.verbose:
                        PRINT.info(f"  Supported platforms:")
                        for entry in group.get_supported_platforms():
                            if len(entry.dependencies) == 0:
                                PRINT.info(f"    - {entry.platform.name} ({entry.architecture.name}) - {entry.input_type} (no deps) -> {entry.output_type}")
                            else:
                                PRINT.info(f"    - {entry.platform.name} ({entry.architecture.name}) - {entry.input_type} ({entry.dependencies}) -> {entry.output_type}")

                    if len(group.stages) > 0:
                        PRINT.info(f"  Stages:")
                        for stage in group.stages:
                            PRINT.info(f"    - {stage}")

                            for k, v in stage.required_parameters.items():
                                PRINT.info(f"      ~ {k}: {v}")

                            deps = stage.get_supported_dependency_types()
                            assert len(deps) >= 1
                            if len(deps) == 1 and len(deps[0]) == 0:
                                PRINT.info(f"      ~ No dependencies")
                            else:
                                PRINT.info(f"      ~ Dependencies required: {sorted(set([len(d) for d in deps]))}")

                            if not options.verbose:
                                continue

                            max_length = math.floor(math.log10(max(1, len(stage.tasks)))) + 1
                            for i, task in enumerate(stage.tasks):
                                PRINT.info(f"      {str(i+1).rjust(max_length, ' ')}. {'<ERROR>' if task is None else task.name}")

                    PRINT.info(f"")

        return True

    def get_pretty_description_header(self) -> str:
        return f"{super().get_pretty_description_header()} [name]"

