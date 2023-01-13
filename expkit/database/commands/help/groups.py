import argparse
import math
import textwrap
from typing import Optional, get_type_hints, List, Tuple

from expkit.base.command.base import CommandTemplate, CommandOptions
from expkit.base.logger import get_logger
from expkit.framework.database import register_command, StageDatabase, GroupDatabase

LOGGER = get_logger(__name__)
PRINT = get_logger(__name__, True)


class HelpOptions(CommandOptions):
    def __init__(self):
        super().__init__()
        self.help_groups: List[str] = []


@register_command
class GroupInfoCommand(CommandTemplate):
    def __init__(self):
        super().__init__(".help.groups", textwrap.dedent('''\
            Print information about groups.
        '''), textwrap.dedent('''\
            Print information about a specific group. If no name is given, a list
            of all groups, is printed.
            When a name is given, the help for the specific group is printed.
            This includes a description and a list of available config parameters.
            '''), options=HelpOptions)

    def create_argparse(self) -> argparse.ArgumentParser:
        parser = super().create_argparse()

        parser.add_argument("name", nargs="*", default=None, help="Name of the group (or 'all') to print information about.")

        return parser

    def parse_arguments(self, *args: str) -> Tuple[HelpOptions, argparse.ArgumentParser, argparse.Namespace]:
        options, parser, namespace = super().parse_arguments(*args)

        options.help_groups = namespace.name

        if "all" in options.help_groups:
            db = GroupDatabase.get_instance()
            options.help_groups = tuple(sorted([s.name for s in db.groups.values()]))

        return options, parser, namespace

    def execute(self, options: HelpOptions) -> bool:
        db = GroupDatabase.get_instance()

        if len(options.help_groups) == 0:
            PRINT.info(f"Printing list of all groups")
            for stage in sorted([stage.name for stage in db.groups.values()]):
                PRINT.info(f" - {stage}")
            PRINT.info("")
        else:
            for name in options.help_groups:
                group = db.get_group(name)
                if group is None:
                    LOGGER.error(f"Group not found: {name}")
                else:
                    PRINT.info(f"Group '{name}'")
                    PRINT.info(textwrap.fill(f"Description: {group.description}", initial_indent='  ', subsequent_indent='    '))

                    if options.log_verbose:
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

                            for k, v in stage.get_required_parameters_info().items():
                                PRINT.info(f"      ~ {k}: {v[0]} {v[1]}")

                            deps = stage.get_supported_dependency_types()
                            assert len(deps) >= 1
                            if len(deps) == 1 and len(deps[0]) == 0:
                                PRINT.info(f"      ~ No dependencies")
                            else:
                                PRINT.info(f"      ~ Dependencies required: {sorted(set([len(d) for d in deps]))}")

                            if not options.log_verbose:
                                continue

                            max_length = math.floor(math.log10(max(1, len(stage.tasks)))) + 1
                            for i, task in enumerate(stage.tasks):
                                PRINT.info(f"      {str(i+1).rjust(max_length, ' ')}. {'<ERROR>' if task is None else task.name}")

                    PRINT.info(f"")

        return True

    def get_pretty_description_header(self) -> str:
        return f"{super().get_pretty_description_header()} [all/name [name ...]]"

