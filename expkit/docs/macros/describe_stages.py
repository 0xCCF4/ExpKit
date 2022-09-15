import textwrap

from expkit.base.architecture import TargetPlatform
from expkit.docs.macros.platform import platform_icon, describe_target_platform
from expkit.framework.database import TaskDatabase, StageDatabase
from expkit.docs.utils import mkdocs_macro, escape_markdown


@mkdocs_macro
def describe_stage_parameters(stage_name: str) -> str:
    db = StageDatabase.get_instance()
    result = ""
    stage = db.get_stage(stage_name)

    if stage is None:
        raise RuntimeError(f"Task not found.")

    result += "Name | Type | Description\n"
    result += " :--- | :--- | :---\n"

    for k, v in stage.get_required_parameters_info().items():
        result += f" {escape_markdown(k)} | {escape_markdown(v[0])} | {escape_markdown(v[1])} \n"

    return result


@mkdocs_macro
def describe_stage(stage_name: str) -> str:
    db = StageDatabase.get_instance()
    result = ""
    stage = db.get_stage(stage_name)

    platform = stage.platform
    pretty_string = platform.get_pretty_string()
    pretty_string_default = pretty_string if pretty_string is not None else "Custom"

    icons = ""
    if not platform.intersection(TargetPlatform.WINDOWS).is_empty():
        icons += platform_icon("windows")
    if not platform.intersection(TargetPlatform.LINUX).is_empty():
        icons += platform_icon("linux")
    if not platform.intersection(TargetPlatform.MACOS).is_empty():
        icons += platform_icon("macos")

    result += f"## {escape_markdown(stage.name)} {icons}\n\n"
    result += f"### Description\n {escape_markdown(stage.description)}\n\n"

    result += f"### Platform\n {escape_markdown(pretty_string_default)}\n\n"

    start_extended = "+" if pretty_string is None else ""
    result += f"???{start_extended} \"Detailed platform overview\"\n\n{textwrap.indent(describe_target_platform(platform), '    ')}\n\n"

    result += f"### Parameters\n"
    if len(stage.required_parameters_types) > 0:
        result += describe_stage_parameters(stage_name)
    else:
        result += "None\n\n"
    result += "\n\n"

    result += "### Accepted dependencies\n"
    for dependencies in stage.get_supported_dependency_types():
        if len(dependencies) <= 0:
            result += f" - No dependencies\n"
        else:
            result += f" - {escape_markdown(', '.join([p.name for p in dependencies]))}\n"

    result += "\n\n### Payload processing\n"

    result += "Input type | Dependencies | Output type\n"
    result += " :--- | :--- | :---\n"
    for input_type in stage.get_supported_input_payload_types():
        for dependencies in stage.get_supported_dependency_types():
            dep_names = [p.name for p in dependencies]
            dep_names = ', '.join(dep_names) if len(dep_names) > 0 else "No dependencies"
            output_types = ', '.join([t.name for t in stage.get_output_payload_type(input_type, dependencies)])
            result += f" {escape_markdown(input_type.name)} | {escape_markdown(dep_names)} | {escape_markdown(output_types)} \n"

    result += "\n\n### Tasks\n"

    if len(stage.tasks) <= 0:
        result += "None\n"
    else:
        result += "Num | Name | Description\n"
        result += " :---: | :--- | :---\n"
        for i, task in enumerate(stage.tasks):
            result += f" {i+1} | [{escape_markdown(task.name)}](tasks.md#{escape_markdown(task.name.replace('.',''))}) | {escape_markdown(task.description)} \n"

    return result



@mkdocs_macro
def describe_stages() -> str:
    result = ""

    db = StageDatabase.get_instance()

    for stage_name in sorted([s.name for s in db.stages.values()]):
        result += describe_stage(stage_name)
        result += "\n\n"
        pass

    return result
