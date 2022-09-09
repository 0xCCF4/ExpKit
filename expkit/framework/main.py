import argparse
import json
import logging
import os
import sys
import textwrap
from json import JSONDecodeError
from pathlib import Path

from expkit.base.command.base import CommandOptions
from expkit.base.logger import get_logger, init_global_logging
from expkit.framework.database import TaskDatabase, auto_discover_databases, GroupDatabase, StageDatabase, \
    CommandDatabase, build_databases

LOGGER = None
PRINT = None


def main():
    global LOGGER, PRINT

    parser = argparse.ArgumentParser(description="TWINSEC exploit building framework", formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output", default=False)
    parser.add_argument("-d", "--debug", action="store_true", help="debug output", default=False)
    parser.add_argument("-f", "--file", help="configuration file to load", type=str, default=None)
    parser.add_argument("-t", "--targets", help="artifact to build, several artifacts can be separated by comma", type=str, default=None)
    parser.add_argument("-o", "--output", help="temporary build directory", type=str, default=None)
    parser.add_argument("-l", "--log", help="log file", type=str, default=None)
    parser.add_argument("-n", "--threads", help="number of threads to use", type=int, default=1)
    parser.add_argument("command", metavar="cmd", type=str, nargs="*",
                        help=textwrap.dedent('''\
                            Command to execute (default: build)
                            
                            help
                                Print help about commands to execute.
                                
                            help cmd <command>
                                Print help about a given command.
                            '''), default=["build"])

    # Parse arguments
    args = parser.parse_args()

    # Setup logging
    if args.debug:
        args.verbose = True

    file_logging_level = logging.INFO
    console_logging_level = logging.WARNING

    if args.verbose:
        console_logging_level = logging.INFO
    if args.debug:
        console_logging_level = logging.DEBUG
        file_logging_level = logging.DEBUG

    log_file = args.log
    if log_file is not None:
        log_file = Path(log_file)

    init_global_logging(log_file, file_logging_level, console_logging_level)
    LOGGER = get_logger("main")
    PRINT = get_logger("main", True)
    LOGGER.info("Hello world")

    if args.verbose:
        LOGGER.info("Printing verbose output")
    if args.debug:
        LOGGER.info("Printing debug output")

    # Load database
    expkit_dir = Path(__file__).parent.parent
    LOGGER.info("Gathering all exploit chain modules")

    auto_discover_databases(expkit_dir)

    external_dbs = os.environ.get("EXPKIT_DB", None)
    if external_dbs is not None:
        external_dbs = external_dbs.split(":")
        for db_config in external_dbs:
            db_config = db_config.split("#")
            if len(db_config) != 2:
                LOGGER.error(f"Invalid database configuration: {db_config}")
                continue

            path, module = db_config
            path = Path(path)

            LOGGER.info(f"Loading external database: {path} ({module})")
            if not path.exists() or not path.is_dir():
                LOGGER.error(f"Invalid database path: {path}")
            else:
                auto_discover_databases(path, module)

    build_databases()
    LOGGER.info(f"Found {len(GroupDatabase.get_instance())} groups, {len(StageDatabase.get_instance())} stages, {len(TaskDatabase.get_instance())} tasks, {len(CommandDatabase.get_instance())} commands")

    # Checking arguments
    LOGGER.debug("Checking arguments")

    config_file = None
    if args.file is not None:
        LOGGER.debug(f"Checking if file {args.file} exists")
        config_file = Path(args.file)
        if not config_file.exists():
            LOGGER.warning(f"Config file {config_file.absolute()} does not exist")
            config_file = None
        elif not config_file.is_file():
            LOGGER.warning(f"Config file {config_file.absolute()} is not a file")
            config_file = None
        LOGGER.debug("Config file exists")

    artifacts = None
    if args.targets is not None:
        artifacts = args.targets.split(",")
        LOGGER.debug(f"Passed list of artifacts to build {artifacts}")

    output_dir = None
    if args.output is not None:
        output_dir = Path(args.output)
        if not output_dir.exists():
            LOGGER.critical(f"Output directory {output_dir} does not exist")
        if not output_dir.is_dir():
            LOGGER.critical(f"Output directory {output_dir} is not a directory")
        LOGGER.debug("Output directory exists")

    if config_file is None:
        LOGGER.info("No config file specified. Using default file_path")
        config_file = Path("config.json")

        if not config_file.exists():
            LOGGER.warning(f"Config file {config_file} does not exist")
            config_file = None
        elif not config_file.is_file():
            LOGGER.warning(f"Config file {config_file} is not a file")
            config_file = None

    config = None
    if config_file is not None:
        try:
            with open(config_file, "r") as f:
                config = json.load(f)
        except JSONDecodeError as e:
            LOGGER.critical(f"Error parsing config file {config_file}: {e}")
        except Exception as e:
            LOGGER.critical(f"Failed to load config file {config_file}")
            raise e

    # Executing command
    LOGGER.debug("Starting main")
    m = CommandDatabase.get_instance().get_command(*args.command)
    if m is None:
        LOGGER.critical(f"Unknown command '{' '.join(args.command)}'. Use 'help' or '--help' to get a list of available commands")
    else:
        cmd, cmd_args = m
        LOGGER.info(f"Executing command {cmd.name[1:]}")
        if not cmd.execute(CommandOptions(config, artifacts, output_dir, args.threads), *cmd_args):
            PRINT.info(f"\n{parser.format_help()}\n")

    LOGGER.debug("Exiting...")


if __name__ == "__main__":
    main()
