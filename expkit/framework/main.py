import argparse
import json
import logging
import sys
from json import JSONDecodeError
from pathlib import Path
from typing import Optional, List

from expkit.base.logger import get_logger, init_global_logging
from expkit.framework.database import TaskDatabase

logger = None


def main(config: dict, artifacts: Optional[List[str]], output_directory: Optional[Path]):
    import expkit.tasks.obfuscation.csharp.string_transform_template
    db = TaskDatabase.get_instance()
    for k, v in db.tasks:
        print(k, v)
    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TWINSEC exploit building framework")

    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output", default=False)
    parser.add_argument("-d", "--debug", action="store_true", help="debug output", default=False)
    parser.add_argument("-f", "--file", help="configuration file to load", type=str, default=None)
    parser.add_argument("-c", "--command", help="artifact to build, several artifacts can be separated by comma", type=str, default=None)
    parser.add_argument("-o", "--output", help="temporary build directory", type=str, default=None)
    parser.add_argument("-l", "--log", help="log file", type=str, default=None)

    args = parser.parse_args()

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
    logger = get_logger("main")
    logger.info("Hello world")

    if args.verbose:
        logger.info("Printing verbose output")
    if args.debug:
        logger.info("Printing debug output")

    logger.debug("Checking arguments")

    config_file = None
    if args.file is not None:
        logger.debug(f"Checking if file {args.file} exists")
        config_file = Path(args.file)
        if not config_file.exists():
            logger.critical(f"Config file {config_file} does not exist")
        if not config_file.is_file():
            logger.critical(f"Config file {config_file} is not a file")
        logger.debug("Config file exists")

    artifacts = None
    if args.command is not None:
        artifacts = args.command.split(",")
        logger.debug(f"Passed list of artifacts to build {artifacts}")

    output_dir = None
    if args.output is not None:
        output_dir = Path(args.output)
        if not output_dir.exists():
            logger.critical(f"Output directory {output_dir} does not exist")
        if not output_dir.is_dir():
            logger.critical(f"Output directory {output_dir} is not a directory")
        logger.debug("Output directory exists")

    if config_file is None:
        logger.debug("No config file specified. Using default file_path")
        config_file = Path("config.json")

        if not config_file.exists():
            logger.critical(f"Config file {config_file} does not exist")
        if not config_file.is_file():
            logger.critical(f"Config file {config_file} is not a file")

    try:
        with open(config_file, "r") as f:
            config = json.load(f)
    except JSONDecodeError as e:
        logger.critical(f"Error parsing config file {config_file}: {e}")
    except Exception as e:
        logger.critical(f"Failed to load config file {config_file}")
        raise e

    logger.debug("Entering main function")
    main(config, artifacts, output_dir)
    logger.debug("Exiting main function")
