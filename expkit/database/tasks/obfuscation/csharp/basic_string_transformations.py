import base64
from typing import Callable

from expkit.database.tasks.obfuscation.csharp.string_transform_template import register_csharp_string_transform_func, \
    CSharpStringTransformTemplateTask


@register_csharp_string_transform_func("base64")
def base64_encode(parent: CSharpStringTransformTemplateTask, parameters: dict, context: dict) -> Callable[[str], str]:
    def csharp_transform_base64(input: str) -> str:
        if len(input) > 0:
            b64 = base64.b64encode(input.encode("utf8")).decode("utf8")
            out = f"Encoding.UTF8.GetString(Convert.FromBase64String(\"{b64}\"))"
        else:
            out = "\"\""
        return out

    return csharp_transform_base64
