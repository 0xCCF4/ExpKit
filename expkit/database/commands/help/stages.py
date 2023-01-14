import argparse
import textwrap
from typing import Optional, get_type_hints, List, Tuple

from expkit.base.command.base import CommandTemplate, CommandOptions
from expkit.base.logger import get_logger
from expkit.framework.database import register_command, StageDatabase

LOGGER = get_logger(__name__)
PRINT = get_logger(__name__, True)


class HelpOptions(CommandOptions):
    def __init__(self):
        super().__init__()
        self.help_stages: List[str] = []


@register_command
class StageInfoCommand(CommandTemplate):
    def __init__(self):
        super().__init__(".help.stages", textwrap.dedent('''\
            Print information about stages.
        '''), textwrap.dedent('''\
            Print information about a specific stage. If no name is given, a list
            of all stages, is printed.
            When a name is given, the help for the specific stage is printed.
            This includes a description and a list of available config parameters.
            '''), options=HelpOptions)

    def create_argparse(self) -> argparse.ArgumentParser:
        parser = super().create_argparse()

        parser.add_argument("name", nargs="*", default=None, help="Name of the stage (or 'all') to print information about.")

        return parser

    def parse_arguments(self, *args: str) -> Tuple[HelpOptions, argparse.ArgumentParser, argparse.Namespace]:
        options, parser, namespace = super().parse_arguments(*args)

        options.help_stages = namespace.name

        if "all" in options.help_stages:
            db = StageDatabase.get_instance()
            options.help_stages = tuple(sorted([s.name for s in db.stages.values()]))

        return options, parser, namespace

    def execute(self, options: HelpOptions) -> bool:
        db = StageDatabase.get_instance()

        if len(options.help_stages) == 0:
            PRINT.info(f"Printing list of all stages")
            for stage in sorted([stage.name for stage in db.stages.values()]):
                PRINT.info(f" - {stage}")
            PRINT.info("")
        else:
            for name in options.help_stages:
                stage = db.get_stage(name)
                if stage is None:
                    LOGGER.error(f"Stage not found: {name}")
                else:
                    PRINT.info(f"Stage '{name}'")
                    PRINT.info(textwrap.fill(f"Description: {stage.description}", initial_indent='  ', subsequent_indent='    '))

                    platform_text = stage.platform.get_pretty_string()
                    if platform_text is not None:
                        PRINT.info(f"  Platform: {platform_text}")
                    else:
                        PRINT.info(f"  Platform:")
                        for platform, architecture in stage.platform:
                            PRINT.info(f"    - {platform} ({architecture})")

                    dependency_types = stage.get_supported_dependency_types()
                    if len(dependency_types) <= 0:
                        LOGGER.error("No dependency types supported - stage is unusable")

                    PRINT.info(f"  Dependencies:")
                    for dependencies in dependency_types:
                        PRINT.info(f"    - {dependencies}")

                    if options.log_verbose:
                        PRINT.info(f"  Supported payload types:")
                        for input_type in stage.get_supported_input_payload_types():
                            for dependencies in dependency_types:
                                if len(dependencies) <= 0:
                                    PRINT.info(f"    - {input_type} (no dependencies) -> {stage.get_output_payload_type(input_type, dependencies)}")
                                else:
                                    PRINT.info(f"    - {input_type} ({dependencies}) -> {stage.get_output_payload_type(input_type, dependencies)}")

                    if len(stage.required_parameters_types) > 0:
                        PRINT.info(f"  Config parameters:")
                        for k, v in stage.get_required_parameters_info().items():
                            PRINT.info(f"    - {k}: {v[0]} {v[1]}")
                    PRINT.info("")

        return True

    def get_pretty_description_header(self) -> str:
        return f"{super().get_pretty_description_header()} [all/name]"

