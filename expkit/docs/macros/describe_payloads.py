import textwrap
from typing import Dict, Tuple, List

from expkit.base.architecture import TargetPlatform, Platform
from expkit.base.payload import PayloadType
from expkit.docs.macros.platform import platform_icon, describe_target_platform
from expkit.framework.database import TaskDatabase, StageDatabase, GroupDatabase
from expkit.docs.utils import mkdocs_macro, escape_markdown, markdown_anchor


@mkdocs_macro
def describe_payload_types() -> str:
    result = ""

    db = PayloadType.get_all_types(include_empty=True)

    result += "Name | Project | File | Binary | Description\n"
    result += " :--- | :---: | :---: | :---: | :---\n"

    for ptype in db:
        project = " :heavy_check_mark: " if ptype.is_project() else " :x: "
        file = " :heavy_check_mark: " if ptype.is_file() else " :x: "
        binary = " :heavy_check_mark: " if ptype.is_binary() else " :x: "

        result += f" {escape_markdown(ptype.name)} | {project} | {file} | {binary} | {escape_markdown(ptype.get_description())} \n"

    return result
