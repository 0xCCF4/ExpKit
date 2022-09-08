import textwrap
from typing import Optional, get_type_hints

from expkit.base.command.base import CommandTemplate, CommandOptions, CommandArgumentCount
from expkit.base.logger import get_logger
from expkit.framework.database import register_command, StageDatabase

LOGGER = get_logger(__name__)
PRINT = get_logger(__name__, True)


@register_command
class StageInfoCommand(CommandTemplate):
    def __init__(self):
        super().__init__(".stages", CommandArgumentCount(0, "*"), textwrap.dedent('''\
            Print information about stages.
        '''), textwrap.dedent('''\
            Print information about a specific stage. If no name is given, a list
            of all stages, is printed.
            When a name is given, the help for the specific stage is printed.
            This includes a description and a list of available config parameters.
            '''))

    def _execute_command(self, options: CommandOptions, *args) -> bool:
        db = StageDatabase.get_instance()

        if len(args) == 1 and args[0] == "all":
            args = tuple([s.name for s in db.stages.values()])

        if len(args) == 0:
            PRINT.info(f"Printing list of all stages")
            for stage in db.stages.values():
                PRINT.info(f" - {stage.name}")
            PRINT.info("")
        else:
            for name in args:
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

                    PRINT.info(f"\n  Dependencies:")
                    for dependencies in dependency_types:
                        PRINT.info(f"    - {dependencies}")

                    PRINT.info(f"  Supported payload types:")

                    for input_type in stage.get_supported_input_payload_types():
                        for dependencies in dependency_types:
                            if len(dependencies) <= 0:
                                PRINT.info(f"    - {input_type} (no dependencies) -> {stage.get_output_payload_type(input_type, dependencies)}")
                            else:
                                PRINT.info(f"    - {input_type} ({dependencies}) -> {stage.get_output_payload_type(input_type, dependencies)}")

                    if len(stage.required_parameters) > 0:
                        PRINT.info(f"  Config parameters:")
                        for k, v in stage.required_parameters.items():
                            PRINT.info(f"    - {k}: {v}")
                    PRINT.info("")

        return True

    def get_pretty_description_header(self) -> str:
        return f"{super().get_pretty_description_header()} [name]"

