import re
from typing import Dict, Optional, Union, List

from expkit.base.logger import get_logger
from expkit.base.architecture import TargetPlatform
from expkit.database.tasks.general.utils.abstract_string_replace import AbstractStringReplace
from expkit.framework.database import register_task


LOGGER = get_logger(__name__)


@register_task
class CSharpAddDefines(AbstractStringReplace):
    def __init__(self):
        super().__init__(
            name="tasks.templating.csharp.csharp_add_defines",
            description="Add defines to C# source files.",
            platform=TargetPlatform.ALL,
            required_parameters=[
                ("defines", List[str], "Defines to add to the source code")
            ]
        )

    def transform_source(self, source: str, parameters: dict) -> str:
        defines = parameters.get("defines", [])

        for define in defines:
            source = f"#define {define}\n{source}"

        return source
