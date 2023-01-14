from expkit.base.architecture import TargetPlatform, Platform, Architecture
from expkit.docs.utils import mkdocs_macro
from expkit.docs.macros.utils import escape_markdown, markdown_anchor


@mkdocs_macro
def platform_icon(platform: str) -> str:
    if platform.lower() == "linux" or platform.lower() == "lin":
        return ":material-penguin:"
    elif platform.lower() == "windows" or platform.lower() == "win":
        return ":material-microsoft-windows:"
    elif platform.lower() == "macos" or platform.lower() == "mac":
        return ":material-apple:"
    else:
        return ""


def describe_target_platform(target: TargetPlatform) -> str:
    platforms = Platform.ALL.get_platforms()
    architectures = Architecture.ALL.get_architectures()

    result = " :fontawesome-solid-microchip: | "
    result += " | ".join([escape_markdown(p.name) for p in platforms])
    result += "\n"
    result += " :---: | " * len(platforms)
    result += " :---: \n"

    for a in architectures:
        result += f" {escape_markdown(a.name)} | "
        for p in platforms:
            if (p, a) in target:
                result += " :heavy_check_mark: | "
            else:
                if a in p.supporting_architectures():
                    result += " :x: | "
                else:
                    result += " | "
        result += "\n"

    return result

