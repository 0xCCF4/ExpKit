import textwrap

from expkit.base.command.base import CommandTemplate, CommandOptions, CommandArgumentCount
from expkit.base.logger import get_logger
from expkit.framework.database import register_command
from ipaddress import ip_address

from expkit.framework.parser import ConfigParser

LOGGER = get_logger(__name__)


@register_command
class ServerCommand(CommandTemplate):
    def __init__(self):
        super().__init__(".build", CommandArgumentCount(0, 2), textwrap.dedent('''\
            Builds an exploit according to the config.json file.
            '''))

    def _execute_command(self, options: CommandOptions, *args) -> bool:
        if options.config is None:
            LOGGER.critical("No config file specified.")

        parser = ConfigParser()
        root = parser.parse(options.config)



        return True
