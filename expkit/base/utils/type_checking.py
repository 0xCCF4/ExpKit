import inspect
from types import FrameType
from typing import Type, Tuple, get_origin, get_args, ForwardRef, Union, List, Dict, TypeVar

from expkit.base.utils.base import error_on_fail, StatusError

T = TypeVar('T')


def get_caller_frame() -> FrameType:
    stack = inspect.stack()
    for frame in stack:
        if frame.filename != __file__:
            return frame.frame

    raise RuntimeError("Could not find caller frame")


def check_type(value: any, expected_type: Type, caller_module=None, caller_locals=None, caller_globals=None) -> StatusError:
    caller_frame = get_caller_frame()
    caller_module_overwrite = inspect.getmodule(caller_frame)
    if caller_module is None:
        caller_module = caller_module_overwrite
    if caller_locals is None:
        caller_locals = caller_frame.f_locals
    if caller_globals is None:
        caller_globals = caller_frame.f_globals

    def check_type_recursive(value: any, t: Type, type_err_prefix: str = "") -> Tuple[bool, str, str]:
        origin = get_origin(t)
        args = get_args(t)

        if origin is None:
            origin = t
        if isinstance(origin, str):
            origin = ForwardRef(origin, module=caller_module)

        if isinstance(origin, ForwardRef):
            new_type: Type = origin._evaluate(caller_globals, caller_locals, recursive_guard=frozenset())
            if isinstance(new_type, ForwardRef):
                raise RuntimeError(f"Type {origin} can not be resolved. Maybe circular import?")
            return check_type_recursive(value, new_type, type_err_prefix)

        elif origin is Union:
            for arg in args:
                if check_type_recursive(value, arg, type_err_prefix=f"{type_err_prefix}.Union")[0]:
                    return True, "", ""
            return False, f"{type_err_prefix}.Union", "None of the union types matched"

        elif origin is any or origin is type(any):
            return True, "", ""

        elif issubclass(origin, List):
            if not isinstance(value, list):
                return False, f"{type_err_prefix}.List", f"{type(value)} is not a list"

            if len(args) == 0:
                return True, "", ""

            assert len(args) == 1

            for entry in value:
                success, path, msg = check_type_recursive(entry, args[0], type_err_prefix=f"{type_err_prefix}.List")
                if not success:
                    return False, path, msg

            return True, "", ""

        elif issubclass(origin, Tuple):
            if not isinstance(value, tuple):
                return False, f"{type_err_prefix}.Tuple", f"{type(value)} is not a tuple"

            if len(args) == 0:
                return True, "", ""

            assert len(args) == len(value)

            for te, e in zip(args, value):
                success, path, msg = check_type_recursive(e, te, type_err_prefix=f"{type_err_prefix}.Tuple._entry")
                if not success:
                    return False, path, msg

            return True, "", ""

        elif issubclass(origin, Dict):
            if not isinstance(value, dict):
                return False, f"{type_err_prefix}.Dict", f"{type(value)} is not a dict"

            if len(args) == 0:
                return True, "", ""

            assert len(args) == 2
            tk, tv = args

            for k, v in value.items():
                if not check_type_recursive(v, tv)[0]:
                    return False, f"{type_err_prefix}Dict._value", f"{k} is not of type {tv}"
                if not check_type_recursive(k, tk)[0]:
                    return False, f"{type_err_prefix}Dict._key", f"{k} is not of type {tk}"

            return True, "", ""

        elif value is None:
            if issubclass(origin, type(None)):
                return True, "", ""

            return False, f"{type_err_prefix}.None", f"{type(value)} is not None"

        else:
            if len(args) == 0:
                if isinstance(value, origin):
                    return True, "", ""

                return False, f"{type_err_prefix}.{origin}", f"{type(value)} is not of type {origin}"

            else:
                return False, f"{type_err_prefix}.{t}", f"Unable to check {type(value)} against {t} ({origin})"

    success, path, msg = check_type_recursive(value, expected_type)
    return success, f"{path} - {msg}"


def type_guard(func: T) -> T:
    assert inspect.isfunction(func)

    signature = inspect.signature(func)
    parameters = signature.parameters

    def wrapped_func(*args, **kwargs) -> any:
        for i, x in enumerate(parameters.items()):
            name, parameter = x
            annotation = parameter.annotation
            if annotation is inspect.Parameter.empty:
                continue
            else:
                if i < len(args) and (parameter.kind != parameter.KEYWORD_ONLY):
                    value = args[i]
                else:
                    value = kwargs.get(name, parameter.default)

                if value == inspect.Parameter.empty:
                    raise ValueError(f"Parameter {name} is not set")

                error_on_fail(check_type(value, annotation), f"Parameter[{i}] {name} has wrong type", error_type=TypeError)

        result = func(*args, **kwargs)

        if signature.return_annotation is not inspect.Parameter.empty:
            error_on_fail(check_type(result, signature.return_annotation), f"Return value has wrong type", error_type=TypeError)

        return result

    return wrapped_func


def check_dict_types(values: Dict[str, any], type_definitions: Dict[str, Type]) -> StatusError:
    for k, t in type_definitions.items():
        v = values.get(k, None)
        success, msg = check_type(v, t)
        if not success:
            return False, f'Field {k} has wrong type {type(v)} instead of {t}'
    return True, None
