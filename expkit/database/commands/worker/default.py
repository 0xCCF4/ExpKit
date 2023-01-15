import argparse
import textwrap
from ipaddress import IPv4Address, ip_address, IPv6Address
from typing import Tuple

from expkit.base.command.base import CommandTemplate, CommandOptions
from expkit.base.logger import get_logger
from expkit.framework.database import register_command

LOGGER = get_logger(__name__)


class WorkerOptions(CommandOptions):
    def __init__(self):
        super().__init__()
        self.port: int = 3333
        self.host: IPv4Address | IPv6Address = ip_address("0.0.0.0")
        self.token: str = ""



@register_command
class WorkerCommand(CommandTemplate):
    def __init__(self):
        # TODO write description
        super().__init__(".worker", textwrap.dedent('''\
            Advertise the current instance as worker node. Clients
            can issue build jobs to worker instances.
            '''), textwrap.dedent('''\
            Advertise the current instance as worker node. TODO
            '''), WorkerOptions)

    def get_pretty_description_header(self) -> str:
        return f"{super().get_pretty_description_header()} --token [TOKEN]"

    def create_argparse(self) -> argparse.ArgumentParser:
        parser = super().create_argparse()
        group = parser.add_argument_group("Worker Options")

        group.add_argument("-p", "--port", type=int, default=3333, help="The port to listen on")
        group.add_argument("-i", "--ip", type=str, default="0.0.0.0", help="The ip address to bind to")
        group.add_argument("-t", "--token", type=str, default=None, required=True, help="A secret token that is used to connect to the worker")

        return parser

    def parse_arguments(self, *args: str) -> Tuple[WorkerOptions, argparse.ArgumentParser, argparse.Namespace]:
        options, parser, args = super().parse_arguments(*args)
        options: WorkerOptions = options

        ip = None
        try:
            ip = ip_address(args.ip)
        except ValueError:
            LOGGER.critical(f"Invalid ip: {args.ip}")
        options.host = ip

        if args.port <= 0 or args.port > 65535:
            LOGGER.critical(f"Port {args.port} is not a valid port number")
        options.port = args.port

        options.token = args.token

        return options, parser, args

    def execute(self, options: WorkerOptions) -> bool:
        # todo

        LOGGER.info(f"Running worker on {options.host}:{options.port}")


        return True
