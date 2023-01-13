import argparse
import json
import shutil
import textwrap
import time
from typing import Tuple, List

from expkit.base.architecture import Platform, Architecture
from expkit.base.command.base import CommandTemplate, CommandOptions
from expkit.base.logger import get_logger
from expkit.framework.building.build_executor import LocalBuildExecutor
from expkit.framework.building.build_job import JobState
from expkit.framework.building.build_organizer import BuildOrganizer
from expkit.framework.database import register_command
from expkit.framework.parser import ConfigParser

LOGGER = get_logger(__name__)


class BuildOptions(CommandOptions):
    def __init__(self):
        super().__init__()     # req  art  plat arch
        self.targets: List[Tuple[str, str, str, str]] = []


@register_command
class BuildCommand(CommandTemplate):
    def __init__(self):
        super().__init__(".build", textwrap.dedent('''\
            Builds an exploit according to the config.json file,
            the specified platform, and architecture.
            '''), textwrap.dedent('''\
            Builds an exploit according to the config.json file,
            the specified platform, and architecture. If no platform
            or architecture is specified, the default non-platform-arch-specific
            specific DUMMY platform or DUMMY architecture is used.
            '''), BuildOptions)

    def get_pretty_description_header(self) -> str:
        return f"{super().get_pretty_description_header()} --target TARGET [TARGET ...]"

    def create_argparse(self) -> argparse.ArgumentParser:
        parser = super().create_argparse()
        group = parser.add_argument_group("Build Options")

        group.add_argument("--target", help="Specify target to build ARTIFACT[:PLATFORM[:ARCH]]", nargs="+", type=str,
                           default=None, required=True)
        group.add_argument("-c", "--config", help="Specify configuration file to load", type=str, default=None)
        group.add_argument("-o", "--output", help="Build output directory", type=str, default=None)
        group.add_argument("-t", "--temp-dir", help="Temporary build directory", type=str, default=None)
        group.add_argument("--cached", action="store_true", default=False, help="Cache artifact build job outputs between calls")

        return parser

    def parse_arguments(self, *args: str) -> Tuple[BuildOptions, argparse.ArgumentParser, argparse.Namespace]:
        options, parser, args = super().parse_arguments(*args)

        options.targets = []

        for target in args.target:
            parts = target.split(":")
            if len(parts) == 1:
                options.targets.append((target, target, "", ""))
            elif len(parts) == 2:
                options.targets.append((target, parts[0], parts[1], ""))
            elif len(parts) == 3:
                options.targets.append((target, parts[0], parts[1], parts[2]))
            else:
                LOGGER.critical(f"Invalid target '{target}'.")

        return options, parser, args

    def execute(self, options: BuildOptions) -> bool:
        if options.config_file is None:
            LOGGER.critical("No config file specified.")

        try:
            with open(options.config_file, "r") as f:
                try:
                    config = json.load(f)
                except json.JSONDecodeError as e:
                    LOGGER.critical(f"Failed to parse config file: {e}")
                    return False
        except PermissionError:
            LOGGER.critical("Could not read config file. Permission denied.")
            return False
        except FileNotFoundError:
            LOGGER.critical(f"Config file '{options.config_file}' does not exist.")
            return False

        parser = ConfigParser()
        root = parser.parse(config)

        build_organizer = BuildOrganizer(root)
        build_organizer.initialize()

        target_jobs = []

        for request, sartifact, splatform, sarch in options.targets:
            artifact = build_organizer.artifact_build_pipeline.get(sartifact, None)

            if len(splatform.strip()) == 0:
                splatform = "DUMMY"

            if artifact is None:
                LOGGER.critical(f"Unknown artifact '{sartifact}' for target '{request}'.")
                return False

            platform = Platform.get_platform_from_name(splatform)

            if platform is None or platform == Platform.UNKNOWN:
                LOGGER.critical(f"Unknown platform '{splatform}' for target '{request}'.")
                return False

            if len(sarch.strip()) == 0:
                sarch = platform.supporting_architectures()[0].name

            architecture = Architecture.get_architecture_from_name(sarch)

            if architecture is None or architecture == Architecture.UNKNOWN:
                LOGGER.critical(f"Unknown architecture '{sarch}' for target '{request}'.")
                return False

            if not platform.is_single():
                LOGGER.critical(f"Platform '{splatform}' is not a valid target. Please specify separate targets")
                return False
            if not architecture.is_single():
                LOGGER.critical(f"Architecture '{sarch}' is not a valid target. Please specify separate targets")
                return False

            assert platform.is_single()
            assert architecture.is_single()

            if architecture not in platform.supporting_architectures():
                LOGGER.critical(f"Platform '{platform.name}' does not support the architecture '{architecture.name}'.")
                return False

            LOGGER.debug(f"Scheduling build for {artifact.config.artifact_name} {platform.name} {architecture.name}")
            target_jobs.extend(build_organizer.queue_job(artifact.config, platform, architecture))

        # Placeholder until caching is introduced
        shutil.rmtree(options.temp_directory)
        options.temp_directory.mkdir(parents=True)

        executor = LocalBuildExecutor(options.temp_directory)
        executor.initialize()

        for job in build_organizer.build():
            LOGGER.debug(f"{len(build_organizer.open_jobs())} jobs are waiting to be built.")
            if job is None:
                LOGGER.info(f"Waiting for {len(build_organizer.building_jobs())} jobs to complete...")
                time.sleep(1)
            else:
                LOGGER.debug(f"Building {job}...")
                try:
                    executor.execute_job(job)
                except Exception as e:
                    LOGGER.error(f"Failed to build {job}: {e}")
                    with job.lock:
                        if job.state.is_pending():
                            job.mark_running()
                        job.mark_error()

        executor.shutdown()

        # Debug print
        #for job, info in build_organizer.scheduling_info.items():
        #    LOGGER.debug(f"{info.name}\t{job}")

        return True
