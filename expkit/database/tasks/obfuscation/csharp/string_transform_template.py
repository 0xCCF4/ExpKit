import re
from typing import  Optional, Callable, Dict

from expkit.base.logger import get_logger
from expkit.base.architecture import TargetPlatform
from expkit.database.tasks.general.utils.abstract_string_replace import AbstractStringReplace
from expkit.framework.database import register_task


TRANSFORMATIONS: Dict[str, Callable[["CSharpStringTransformTemplateTask", dict, dict], Callable[[str], str]]] = {}


def register_csharp_string_transform_func(*args, **kwargs):
    def decorator(func):
        name = args[0]

        if name in TRANSFORMATIONS:
            raise ValueError(f"Transformation {name} already registered")

        TRANSFORMATIONS[name] = func
        return func

    if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
        raise ValueError("Decorator must be called with transformation name as parameter")
    if len(args) > 1:
        raise ValueError("Decorator must be called with transformation name as parameter")
    if len(kwargs) > 0:
        raise ValueError("Decorator must be called with transformation name as parameter")
    assert len(args) == 1 and len(kwargs) == 0 and callable(args[0]) is False, "Decorator must be called with transformation name as parameter"
    if len(args) == 1 and not isinstance(args[0], str):
        raise ValueError("Decorator must be called with transformation name as parameter")

    return decorator


LOGGER = get_logger(__name__)

STATUS_NORMAL = 0
STATUS_STRING = 1
STATUS_AT_STRING = 2


@register_task
class CSharpStringTransformTemplateTask(AbstractStringReplace):
    def __init__(self):
        super().__init__(
            name="tasks.obfuscation.csharp.string_transform_template",
            description="Transforms all strings within CSharp source code to prevent signature detection of used strings.",
            platform=TargetPlatform.ALL,
            required_parameters={
                "OBF_STRING_ENCODING": Optional[str]
            } 
        )

        self.__status: int = 0
        self.__transform_func = None

    def transform_source(self, source: str, parameters: dict) -> str:
        method = parameters.get("OBF_STRING_ENCODING", "base64")

        transform = TRANSFORMATIONS.get(method, None)
        if transform is None:
            LOGGER.error(f"Unknown string encoding {method}")
            raise ValueError(f"Unknown string encoding {method}")

        LOGGER.debug(f"Transforming strings using {method}")
        return self._transform(source, parameters, transform)

    def _transform(self, source: str, parameters: dict, transform: Callable[["CSharpStringTransformTemplateTask", dict, dict], Callable[[str], str]]) -> str:
        context = {}
        with self._lock:
            self.__status = STATUS_NORMAL
            self.__transform_func = transform(self, parameters, context)

            old_source = ""
            cmp = re.compile(r'(@)?(\"[^\"]|\"\")', re.MULTILINE | re.DOTALL)
            while old_source != source:
                old_source = source
                source = cmp.sub(self._parse_source, source, count=1)
            source = source.replace("\\{{CONTINUE_NA_STRING}}", "{{CONTINUE_NA_STRING}}")

            cmp = re.compile(r'(\{\{BEGIN_NA_STRING\}\})(.*?)(\{\{END_NA_STRING\}\})', re.MULTILINE | re.DOTALL)
            source = cmp.sub(self._replace_strings_normal, source)
            cmp = re.compile(r'(\{\{BEGIN_AT_STRING\}\})(.*?)(\{\{END_AT_STRING\}\})', re.MULTILINE | re.DOTALL)
            source = cmp.sub(self._replace_strings_at, source)
            return source

    def _parse_source(self, match: re.Match) -> str:
        assert self._lock.locked()

        index = match.start()

        escaped_quote = False

        while index - 1 > 0:
            if match.string[index - 1] == "\\":
                escaped_quote = not escaped_quote
                index -= 1
            else:
                break

        at_sign = match.group(1) == "@"
        double_quote = match.group(2) == "\"\""
        prefix = "" if match.group(1) is None else match.group(1)
        postfix = match.group(2)[1:]

        result = match.group(0)

        if self.__status == STATUS_NORMAL:  # no string
            if at_sign:
                self.__status = STATUS_AT_STRING  # @ string
                token = "{{BEGIN_AT_STRING}}"
                result = token + postfix
            else:
                self.__status = STATUS_STRING  # normal string
                token = "{{BEGIN_NA_STRING}}"
                result = token + postfix
        elif self.__status == STATUS_AT_STRING:  # @ string
            if double_quote:
                token = "{{CONTINUE_AT_STRING}}"
                result = prefix + token
            else:
                self.__status = STATUS_NORMAL
                token = "{{END_AT_STRING}}"
                result = prefix + token + postfix
        elif self.__status == STATUS_STRING:  # normal string
            if escaped_quote:
                token = "{{CONTINUE_NA_STRING}}"
                result = prefix + token + postfix
            else:
                self.__status = STATUS_NORMAL
                token = "{{END_NA_STRING}}"
                result = prefix + token + postfix

        # print(match.string[index:match.start()], match.group(0), " --> ", result)
        return result

    def _replace_strings_normal(self, match: re.Match) -> str:
        assert self._lock.locked()

        # prefix = match.group(1)
        content: str = match.group(2)
        # postfix = match.group(3)

        def replace_slash(m):
            index = m.start()
            escape = False

            while index - 1 > 0:
                if m.string[index - 1] == "\\":
                    escape = not escape
                    index -= 1
                else:
                    break

            if escape:
                return m.group(0)

            operator = m.group(1)
            if operator == "\\":
                return "{{BL}}"
            elif operator == "n":
                return "\n"
            elif operator == "r":
                return "\r"
            elif operator == "t":
                return "\t"
            elif operator == "b":
                return "\b"
            elif operator == "'":
                return "\'"
            elif operator == "\"":
                return "\""
            elif operator == "0":
                return "\0"
            else:
                raise ValueError(f"Unknown operator {operator}")

        content_old = ""
        content_resolved = content
        while content_old != content_resolved:
            content_old = content_resolved
            content_resolved = re.sub(r'\\(.)', replace_slash, content_resolved, count=1)

        content_resolved = content_resolved.replace("{{BL}}", "\\")

        out = "{{BEGIN_AT_STRING}}" + content_resolved + "{{END_AT_STRING}}"
        # print(str(match.group(0)), " --> ", content, " --> ", content_resolved, " --> ", out)
        return out

    def _replace_strings_at(self, match: re.Match) -> str:
        assert self._lock.locked()

        content: str = match.group(2)
        content = content.replace("{{CONTINUE_NA_STRING}}", "\\\"")
        content = content.replace("{{CONTINUE_AT_STRING}}", "\"")

        return self.__transform_func(content)
