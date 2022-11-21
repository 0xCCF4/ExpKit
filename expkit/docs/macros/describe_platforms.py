from expkit.base.architecture import Platform, Architecture
from expkit.docs.utils import mkdocs_macro
from expkit.docs.macros.utils import escape_markdown, markdown_anchor


@mkdocs_macro
def describe_platforms() -> str:
    result = ""

    platforms = Platform.ALL.get_platforms()
    architectures = Architecture.ALL.get_architectures()

    result += f":fontawesome-solid-microchip: | {' | '.join([escape_markdown(p.name) for p in architectures])}\n"
    result += f" :--- {'| :---: '*len(architectures)}\n"

    for p in platforms:
        result += f" __{escape_markdown(p.name)}__ | "
        supported = p.supporting_architectures()
        first = True
        for a in architectures:
            if first:
                first = False
            else:
                result += " | "
            result += " :heavy_check_mark: " if a in supported else " :x: "
        result += "\n"

    return result
