import textwrap

from expkit.base.command.base import CommandTemplate, CommandOptions
from expkit.base.logger import get_logger
from expkit.framework.database import register_command


LOGGER = get_logger(__name__)
PRINT = get_logger(__name__, True)


# todo migrate to argparse system
@register_command
class HelpCommandDefault(CommandTemplate):
    def __init__(self):
        super().__init__(".help", textwrap.dedent('''\
            Print help.
            '''))

        self._help_text = "<help text not built>"

    def execute(self, options: CommandOptions, *args) -> bool:
        if len(self._help_text) < 5:
            LOGGER.warning(f"No help text / commands? found.")

        if len(args):
            LOGGER.error(f"Unknown arguments: {args} for command help. Did you meant to type 'help cmd {' '.join(args)}'?")

        PRINT.info(f"\nAvailable commands:\n{self._help_text}\n")

        return True

    def get_pretty_description_header(self) -> str:
        children_names = sorted([child.get_real_name() for child in self.children])
        return f"{super().get_pretty_description_header()} [{'/'.join(children_names)}]"

    def finalize(self):
        root = self
        while root.parent is not None:
            root = root.parent

        all_cmds = root.get_children(recursive=True, order_child_first=True)

        help_texts = []
        for cmd in all_cmds:
            help_texts.append(f"{cmd.get_pretty_description(short_description=True)}")

        self._help_text = "\n\n".join(help_texts)
