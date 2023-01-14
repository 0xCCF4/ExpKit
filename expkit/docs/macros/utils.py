from expkit.docs.utils import mkdocs_macro


@mkdocs_macro
def escape_markdown(string: any) -> str:
    result = ""
    string = f"{string}"
    for c in string:
        result += f"\\{c}"
    return result


@mkdocs_macro
def markdown_anchor(string: any) -> str:
    return string.lower().replace(".", "").replace(" ", "-")
