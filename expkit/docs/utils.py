
__macro_store = {}


def mkdocs_macro(*args, **kwargs):
    def decorator(func):
        if not getattr(func, "__macro_store", False):
            __macro_store[func.__name__] = func
            setattr(func, "__macro_store", True)
        return func

    if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
        # no parameters for decorator
        func = args[0]
        args = ()
        return decorator(func)
    else:
        # parameters for decorator
        return decorator


def get_macros() -> dict:
    global __macro_store

    store = __macro_store
    __macro_store = {}
    return store


@mkdocs_macro
def escape_markdown(string: any) -> str:
    result = ""
    string = f"{string}"
    for c in string:
        result += f"\\{c}"
    return result


@mkdocs_macro
def markdown_anchor(string: any) -> str:
    return string.lower().replace(".", "")
