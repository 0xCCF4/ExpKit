import textwrap
from typing import Dict, Tuple, List

from expkit.base.architecture import TargetPlatform, Platform
from expkit.docs.macros.platform import platform_icon, describe_target_platform
from expkit.framework.database import TaskDatabase, StageDatabase, GroupDatabase
from expkit.docs.utils import mkdocs_macro
from expkit.docs.macros.utils import escape_markdown, markdown_anchor


@mkdocs_macro
def describe_group(stage_name: str) -> str:
    db = GroupDatabase.get_instance()
    result = ""
    group = db.get_group(stage_name)

    platform_overview = TargetPlatform.NONE
    for e in group.get_supported_platforms():
        platform_overview = platform_overview.union(TargetPlatform(e.platform, e.architecture))

    icons = ""
    if not platform_overview.intersection(TargetPlatform.WINDOWS).is_empty():
        icons += platform_icon("windows")
    if not platform_overview.intersection(TargetPlatform.LINUX).is_empty():
        icons += platform_icon("linux")
    if not platform_overview.intersection(TargetPlatform.MACOS).is_empty():
        icons += platform_icon("macos")

    result += f"## {escape_markdown(group.name)} {icons}\n"
    result += "---------------\n"
    result += f"### Description\n {escape_markdown(group.description)}\n\n"

    params: Dict[Tuple[str, any, str], List[int]] = {}
    for i, stage in enumerate(group.stages):
        for pname, pinfo in stage.get_required_parameters_info().items():
            if (pname, pinfo[0], pinfo[1]) in params:
                params[(pname, pinfo[0], pinfo[1])].append(i)
            else:
                params[(pname, pinfo[0], pinfo[1])] = [i]

    result += f"### Parameters \n\n"
    if len(params) > 0:
        result += f"Origin | Name | Type | Description\n"
        result += f":---: | :--- | :--- | :---\n"

        for (pname, ptype, pdescription), indices in params.items():
            ref_stages = [s for i, s in enumerate(group.stages) if i in indices]
            ref_stages_lnk = ", ".join([f"[{i+1}](stages.md#{escape_markdown(markdown_anchor(s.name))})" for i, s in enumerate(ref_stages)])
            result += f"{ref_stages_lnk} | {escape_markdown(pname)} | {escape_markdown(ptype)} | {escape_markdown(pdescription)}\n"
    else:
        result += "None\n\n"

    result += f"\n### Payload processing\n\n"

    result += f":material-desktop-classic: | :fontawesome-solid-microchip: | Input | Dependencies | Output | Stage\n"
    result += f":---: | :---: | :--- | :--- | :--- | :---: \n"
    for e in group.get_supported_platforms():
        icon = escape_markdown(e.platform.name)
        if e.platform == Platform.WINDOWS:
            icon = platform_icon("windows")
        elif e.platform == Platform.LINUX:
            icon = platform_icon("linux")
        elif e.platform == Platform.MACOS:
            icon = platform_icon("macos")

        if len(e.dependencies) <= 0:
            deps = "No dependencies"
        else:
            deps = ", ".join([d.name for d in e.dependencies])

        stage_indecies = []
        for estage in e.stages:
            for i, stage in enumerate(group.stages):
                if estage == stage:
                    stage_indecies.append(i)
                    break
        assert len(stage_indecies) == len(e.stages)

        stage_lnk = ", ".join([f"[{i+1}](stages.md#{escape_markdown(markdown_anchor(s.name))})" for i, s in zip(stage_indecies, e.stages)])

        result += f"{icon} | {escape_markdown(e.architecture.name)} | {escape_markdown(e.input_type.name)} | {escape_markdown(deps)} | {escape_markdown(e.output_type.name)} | {stage_lnk}\n"


    result += "\n\n### Associated stages\n"

    if len(group.stages) <= 0:
        result += "None\n"
    else:
        result += " Num | Name | Description\n"
        result += f" :---: | :---: | :---\n"
        for i, stage in enumerate(group.stages):
            platform = stage.platform
            icons = ""
            if not platform.intersection(TargetPlatform.WINDOWS).is_empty():
                icons += platform_icon("windows")
            if not platform.intersection(TargetPlatform.LINUX).is_empty():
                icons += platform_icon("linux")
            if not platform.intersection(TargetPlatform.MACOS).is_empty():
                icons += platform_icon("macos")

            result += f" {i+1} | [{escape_markdown(stage.name)}](stages.md#{escape_markdown(markdown_anchor(stage.name))}) {icons} | {escape_markdown(stage.description)} \n"

    return result



@mkdocs_macro
def describe_groups() -> str:
    result = ""

    db = GroupDatabase.get_instance()

    for group_name in sorted([g.name for g in db.groups.values()]):
        result += describe_group(group_name)
        result += "\n\n"
        pass

    return result
