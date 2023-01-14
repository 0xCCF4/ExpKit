import argparse
import textwrap
from typing import Optional, get_type_hints, List, Tuple

from expkit.base.command.base import CommandTemplate, CommandOptions
from expkit.base.logger import get_logger
from expkit.framework.database import register_command, StageDatabase, GroupDatabase, TaskDatabase

LOGGER = get_logger(__name__)
PRINT = get_logger(__name__, True)


class HelpOptions(CommandOptions):
    def __init__(self):
        super().__init__()
        self.help_tasks: List[str] = []


@register_command
class TaskInfoCommand(CommandTemplate):
    def __init__(self):
        super().__init__(".help.tasks", textwrap.dedent('''\
            Print information about tasks.
        '''), textwrap.dedent('''\
            Print information about a specific task. If no name is given, a list
            of all tasks, is printed.
            When a name is given, the help for the specific task is printed.
            This includes a description and a list of available config parameters.
            '''), options=HelpOptions)

    def create_argparse(self) -> argparse.ArgumentParser:
        parser = super().create_argparse()

        parser.add_argument("name", nargs="*", default=None, help="Name of the task (or 'all') to print information about.")

        return parser

    def parse_arguments(self, *args: str) -> Tuple[HelpOptions, argparse.ArgumentParser, argparse.Namespace]:
        options, parser, namespace = super().parse_arguments(*args)

        options.help_tasks = namespace.name

        if "all" in options.help_tasks:
            db = TaskDatabase.get_instance()
            options.help_tasks = tuple(sorted([s.name for s in db.tasks.values()]))

        return options, parser, namespace

    def execute(self, options: HelpOptions) -> bool:
        db = TaskDatabase.get_instance()

        if len(options.help_tasks) == 0:
            PRINT.info(f"Printing list of all tasks")
            for task in sorted([task.name for task in db.tasks.values()]):
                PRINT.info(f" - {task}")
            PRINT.info("")
        else:
            for name in options.help_tasks:
                task = db.get_task(name)
                if task is None:
                    LOGGER.error(f"Task not found: {name}")
                else:
                    PRINT.info(f"Task '{name}'")
                    PRINT.info(textwrap.fill(f"Description: {task.description}", initial_indent='  ', subsequent_indent='    '))

                    platform = task.platform
                    platform_text = platform.get_pretty_string()
                    if platform_text is not None:
                        PRINT.info(f"  Platform: {platform_text}")
                    else:
                        PRINT.info(f"  Platform:")
                        for platform, architecture in platform:
                            PRINT.info(f"    - {platform} ({architecture})")

                    if len(task.required_parameters_types) > 0:
                        PRINT.info(f"  Config parameters:")
                        for k, v in task.get_required_parameters_info().items():
                            PRINT.info(f"    - {k}: {v[0]} {v[1]}")

                    PRINT.info("")

        return True

    def get_pretty_description_header(self) -> str:
        return f"{super().get_pretty_description_header()} [all/name]"

