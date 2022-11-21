import textwrap

from expkit.base.architecture import TargetPlatform
from expkit.docs.macros.platform import platform_icon, describe_target_platform
from expkit.framework.database import TaskDatabase, StageDatabase
from expkit.docs.utils import mkdocs_macro
from expkit.docs.macros.utils import escape_markdown, markdown_anchor


@mkdocs_macro
def describe_task_parameters(task_name: str) -> str:
    db = TaskDatabase.get_instance()
    result = ""
    task = db.get_task(task_name)

    if task is None:
        raise RuntimeError(f"Task not found.")

    result += "Name | Type | Description\n"
    result += " :--- | :--- | :---\n"

    for k, v in task.get_required_parameters_info().items():
        result += f" {escape_markdown(k)} | {escape_markdown(v[0])} | {escape_markdown(v[1])} \n"

    return result


@mkdocs_macro
def describe_task(task_name: str) -> str:
    db = TaskDatabase.get_instance()
    result = ""
    task = db.get_task(task_name)

    platform = task.platform

    icons = ""
    if not platform.intersection(TargetPlatform.WINDOWS).is_empty():
        icons += platform_icon("windows")
    if not platform.intersection(TargetPlatform.LINUX).is_empty():
        icons += platform_icon("linux")
    if not platform.intersection(TargetPlatform.MACOS).is_empty():
        icons += platform_icon("macos")

    result += f"## {escape_markdown(task.name)} {icons}\n\n"
    result += "---------------\n"
    result += f"### Description\n {escape_markdown(task.description)}\n\n"

    result += f"### Platform\n\n"

    result += f"{describe_target_platform(platform)}\n\n"

    result += f"### Parameters\n"
    result += describe_task_parameters(task_name)
    result += "\n\n"

    result += "### Used by stages\n\n"
    used_by_stages = [s for s in StageDatabase.get_instance().stages.values() if task in s.tasks]
    if len(used_by_stages) <= 0:
        result += "None\n\n"
    else:
        for stage in used_by_stages:
            result += f" * [{escape_markdown(stage.name)}](stages.md#{escape_markdown(markdown_anchor(stage.name))})\n\n"

    return result



@mkdocs_macro
def describe_tasks() -> str:
    result = ""

    db = TaskDatabase.get_instance()

    for task_name in sorted([t.name for t in db.tasks.values()]):
        result += describe_task(task_name)
        result += "\n\n"

    return result
