import argparse
import json
import logging
import sys
import textwrap
from json import JSONDecodeError
from pathlib import Path
from typing import Optional, List

from expkit.base.logger import get_logger, init_global_logging
from expkit.framework.database import TaskDatabase, auto_discover_databases, StageGroupDatabase, StageDatabase
from expkit.framework.parser import ConfigParser

LOGGER = None


def main(config: dict, artifacts: Optional[List[str]], output_directory: Optional[Path], num_threads: int):


    parser = ConfigParser()
    parsed = parser.parse(config, artifacts)

    print(parser.get_build_plan())

    pass


def main_help(type: Optional[str] = None, name: Optional[str] = None):
    pass


def entry():
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
                            
                            build
                                Builds the exploit configuration defined in the config.json file
                                
                            server [port] [ip]
                                Starts a webserver to build the exploit configuration defined in
                                the config.json file on the fly whenever a request is received.
                                The request must be a GET request with the following parameters:
                                    - platform: The target platform (WINDOWS, LINUX, MACOS, ...)
                                    - arch: The target architecture (i386, AMD64, ARM, ARM64, ...)
                                    - target: The target artifact to build from the config.json file
                                The response will the BASE64 encoded payload. If the payload is
                                platform independent, the platform and arch parameters should be
                                set to "DUMMY". An error will be signaled using the status code
                                500. A json object with an error message will be returned. The
                                server will listen on port 8080 and bound to ip 0.0.0.0 by default.
                            
                            help [stage|task|group] [name]
                                Print help for a stage, task or group. If no name is given, a list
                                of all stages, tasks or groups is printed.
                                When a name is given, the help for the specific stage, task or group
                                is printed. This includes a description and a list of available config
                                parameters.
                                
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
    LOGGER.info("Hello world")

    if args.verbose:
        LOGGER.info("Printing verbose output")
    if args.debug:
        LOGGER.info("Printing debug output")

    # Load database
    expkit_dir = Path(__file__).parent.parent
    LOGGER.info("Gathering all exploit chain modules")
    auto_discover_databases(expkit_dir)  # must only be called once
    LOGGER.info(f"Found {len(StageGroupDatabase.get_instance())} groups, {len(StageDatabase.get_instance())} stages, {len(TaskDatabase.get_instance())} tasks")



    # Checking arguments
    LOGGER.debug("Checking arguments")

    config_file = None
    if args.file is not None:
        LOGGER.debug(f"Checking if file {args.file} exists")
        config_file = Path(args.file)
        if not config_file.exists():
            LOGGER.critical(f"Config file {config_file} does not exist")
        if not config_file.is_file():
            LOGGER.critical(f"Config file {config_file} is not a file")
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
        LOGGER.debug("No config file specified. Using default file_path")
        config_file = Path("config.json")

        if not config_file.exists():
            LOGGER.critical(f"Config file {config_file} does not exist")
        if not config_file.is_file():
            LOGGER.critical(f"Config file {config_file} is not a file")

    try:
        with open(config_file, "r") as f:
            config = json.load(f)
    except JSONDecodeError as e:
        LOGGER.critical(f"Error parsing config file {config_file}: {e}")
    except Exception as e:
        LOGGER.critical(f"Failed to load config file {config_file}")
        raise e

    # Execute main
    LOGGER.debug("Starting main")
    main(config, artifacts, output_dir, args.threads, args.command)
    LOGGER.debug("Exiting...")


if __name__ == "__main__":
    entry()
