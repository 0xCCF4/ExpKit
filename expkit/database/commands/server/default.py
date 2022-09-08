import textwrap

from expkit.base.command.base import CommandTemplate, CommandOptions, CommandArgumentCount
from expkit.base.logger import get_logger
from expkit.framework.database import register_command
from ipaddress import ip_address


LOGGER = get_logger(__name__)


@register_command
class ServerCommand(CommandTemplate):
    def __init__(self):
        super().__init__(".server", CommandArgumentCount(0, 2), textwrap.dedent('''\
            Builds and serves an exploit on the fly when a client connects to the local server.
            '''), textwrap.dedent('''\
            Starts a webserver to build the exploit configuration defined in
            the config.json file on the fly whenever a request is received.
            The request must be a GET request with the following parameters:
            1. platform: The target platform (WINDOWS, LINUX, MACOS, ...).
            2. arch: The target architecture (i386, AMD64, ARM, ARM64, ...).
            3. target: The target artifact to build from the config.json file.
            The response will the BASE64 encoded payload. If the payload is
            platform independent, the platform and arch parameters should be
            set to "DUMMY". An error will be signaled using the status code
            500. A json object with an error message will be returned. The
            server will listen on port 8080 and bound to ip 0.0.0.0 by default.
            '''))

    def get_pretty_description_header(self) -> str:
        return f"{super().get_pretty_description_header()} [port] [ip]"

    def _execute_command(self, options: CommandOptions, *args) -> bool:
        port = 8080
        ip = "0.0.0.0"

        if len(args) > 0:
            if str(port).isnumeric():
                port = int(args[0])
            else:
                LOGGER.critical(f"Invalid port: {args[0]}")
                return False

        if len(args) > 1:
            ip = args[1]
            try:
                ip = ip_address(ip)
            except ValueError:
                LOGGER.critical(f"Invalid ip: {ip}")
                return False

        LOGGER.info(f"Starting server on {ip}:{port}")

        raise NotImplementedError("Not implemented")
