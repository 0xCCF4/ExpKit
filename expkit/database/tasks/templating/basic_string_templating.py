import re
from typing import Dict, Optional, Union

from expkit.base.logger import get_logger
from expkit.base.architecture import TargetPlatform
from expkit.database.tasks.general.utils.abstract_string_replace import AbstractStringReplace
from expkit.framework.database import register_task


LOGGER = get_logger(__name__)


@register_task
class BasicStringTemplating(AbstractStringReplace):
    def __init__(self):
        super().__init__(
            name="tasks.templating.basic_string_templating",
            description="Replaces strings in source file with replacements. Supports regex.",
            platform=TargetPlatform.ALL,
            required_parameters=[
                ("replacements", Dict[str, str], "Replacements to apply. List of regex and replacement pairs"),
                ("regex", Optional[bool], "Enables regex matching (default: True)"),
                ("flags", Optional[Union[int, re.RegexFlag]], "Regex flags (default: re.MULTILINE|re.DOTALL)"),
            ]
        )

    def transform_source(self, source: str, parameters: dict) -> str:
        enable_regex = parameters.get("regex", True)
        flags = parameters.get("flags", re.MULTILINE | re.DOTALL)

        for regex, replacement in parameters["replacements"].items():
            if enable_regex:
                source = re.sub(regex, replacement, source, flags=flags)
            else:
                source = source.replace(regex, replacement)
        return source
