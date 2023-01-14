import argparse
import json
import logging
import os
import sys
import tempfile
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

    parser = argparse.ArgumentParser(description="Exploit/Payload building framework", formatter_class=argparse.RawTextHelpFormatter, add_help=False)

    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output", default=False)
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug output", default=False)
    parser.add_argument("-l", "--log", help="Log file", type=str, default=None)
    parser.add_argument("-h", "--help", help="Show help dialog", action="store_true", default=False)

    parser.add_argument("command", metavar="cmd", type=str, nargs="*",
                        help=textwrap.dedent('''\
                            Command to execute (default: build)
                            
                            help
                                Print help about commands to execute.
                                
                            help cmd <command>
                                Print help about a given command.
                            '''), default=["build"])

    # Parse arguments
    args = parser.parse_known_args()[0]

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

    target_cmd = []
    for arg in sys.argv[1:]:
        if arg.startswith("-"):
            break
        target_cmd.append(arg)

    # Executing command
    LOGGER.debug("Starting main")
    m = CommandDatabase.get_instance().get_command(*sys.argv[1:])
    if m is None:
        LOGGER.critical(f"Unknown command '{' '.join(target_cmd)}'. Use 'help' or '--help' to get a list of available commands")
    else:
        cmd, cmd_args = m
        if cmd.name == '':
            if args.help:
                PRINT.critical(f"\n{parser.format_help()}\n")
            else:
                LOGGER.critical(f"Unknown command '{' '.join(target_cmd)}'. Use 'help' or '--help' to get a list of available commands")

        LOGGER.info(f"Executing command {cmd.name[1:]}")
        options, parser, _ = cmd.parse_arguments(*cmd_args)
        if not cmd.execute(options):
            PRINT.info(f"\n{parser.format_help()}\n")

    LOGGER.debug("Exiting...")


if __name__ == "__main__":
    main()
