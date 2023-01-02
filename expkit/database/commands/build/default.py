import textwrap
import time

from expkit.base.architecture import Platform, Architecture
from expkit.base.command.base import CommandTemplate, CommandOptions, CommandArgumentCount
from expkit.base.logger import get_logger
from expkit.framework.building.build_executor import LocalBuildExecutor
from expkit.framework.building.build_organizer import BuildOrganizer
from expkit.framework.database import register_command
from expkit.framework.parser import ConfigParser

LOGGER = get_logger(__name__)


@register_command
class ServerCommand(CommandTemplate):
    def __init__(self):
        super().__init__(".build", CommandArgumentCount(0, 2), textwrap.dedent('''\
            Builds an exploit according to the config.json file,
            the specified platform, and architecture.
            '''), textwrap.dedent('''\
            Builds an exploit according to the config.json file,
            the specified platform, and architecture. If no platform
            or architecture is specified, the default non-platform-arch-specific
            specific DUMMY platform or DUMMY architecture is used.
            '''))

    def get_pretty_description_header(self) -> str:
        return f"{super().get_pretty_description_header()} [platform] [architecture]"

    def _execute_command(self, options: CommandOptions, *args) -> bool:
        if options.config is None:
            LOGGER.critical("No config file specified.")

        platform = Platform.DUMMY
        architecture = Architecture.DUMMY

        if len(args) <= 0:
            LOGGER.warning("No platform specified. Using DUMMY platform.")
        else:
            platform = Platform.get_platform_from_name(args[0])

        if len(args) <= 1:
            LOGGER.warning("No architecture specified. Using DUMMY architecture.")
        else:
            architecture = Architecture.get_architecture_from_name(args[1])

        if platform is None or platform == Platform.UNKNOWN:
            LOGGER.critical(f"Unknown platform '{args[0]}'.")
        if architecture is None or architecture == Architecture.UNKNOWN:
            LOGGER.critical(f"Unknown architecture '{args[1]}'.")

        assert platform.is_single()
        assert architecture.is_single()

        parser = ConfigParser()
        root = parser.parse(options.config)

        build_organizer = BuildOrganizer(root)
        build_organizer.initialize()

        if options.artifacts is None:
            for artifact in root.build_order:
                build_organizer.queue_job(artifact, platform, architecture)

        else:
            for artifact in options.artifacts:
                build_organizer.queue_job(artifact, platform, architecture)

        # Placeholder
        executor = LocalBuildExecutor()
        executor.initialize()

        for job, nBuilding, nWaiting in build_organizer.build():
            LOGGER.debug(f"{nWaiting} jobs are waiting to be built.")
            if job is None:
                LOGGER.info(f"Waiting for {nBuilding} jobs to complete...")
                time.sleep(1)
            else:
                executor.execute_job(job)

        executor.shutdown()

        return True
