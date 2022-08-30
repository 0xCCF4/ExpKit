import copy
import inspect
from pathlib import Path
from typing import Type, Union, get_args, get_origin, Dict, Tuple, Optional, List, Callable, get_type_hints, ForwardRef, \
    TypeVar

StatusError = Tuple[bool, Optional[str]]


def is_optional_type(field: Type) -> bool:
    return get_origin(field) is Union and type(None) in get_args(field)


def is_dict_type(field: Type) -> bool:
    return get_origin(field) is Dict


def check_dict_types(type_definitions: Dict[str, Type], values: Dict[str, any]) -> StatusError:
    for k, t in type_definitions.items():
        v = values.get(k, None)
        success, msg = check_type(t, v)
        if not success:
            return False, f'Field {k} has wrong type {type(v)} instead of {t}'
    return True, None


def error_on_fail(status: StatusError, msg: str, error_type:Type[Exception]=ValueError, error_status=False) -> StatusError:
    code, nested_msg = status
    if code == error_status:
        raise error_type(f"{msg} {nested_msg}")
    return status


def error_on_fail_any(status: List[StatusError], msg: str, error_type=ValueError, error_status=False) -> List[StatusError]:
    for s in status:
        error_on_fail(s, msg, error_type, error_status)
    return status


def check_type(expected_type: Type, value: any) -> StatusError:

    def check_type_recursive(t: Type, value: any, type_err_prefix:str="") -> Tuple[bool, str, str]:
        origin = get_origin(t)
        args = get_args(t)

        if origin is None:
            origin = t

        if isinstance(t, ForwardRef):
            new_type: Type = t._evaluate(globals(), locals(), frozenset())
            if isinstance(new_type, ForwardRef):
                raise RuntimeError(f"Type {t} can not be resolved. Maybe circular import?")
            return check_type_recursive(new_type, value, type_err_prefix)

        elif origin is Union:
            for arg in args:
                if check_type_recursive(arg, value, type_err_prefix=f"{type_err_prefix}.Union")[0]:
                    return True, "", ""
            return False, f"{type_err_prefix}.Union", "None of the union types matched"

        elif issubclass(origin, type(any)):
            return True, "", ""

        elif issubclass(origin, List):
            if not isinstance(value, list):
                return False, f"{type_err_prefix}.List", f"{type(value)} is not a list"

            if len(args) == 0:
                return True, "", ""

            assert len(args) == 1

            for entry in value:
                success, path, msg = check_type_recursive(args[0], entry, type_err_prefix=f"{type_err_prefix}.List")
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
                success, path, msg = check_type_recursive(te, e, type_err_prefix=f"{type_err_prefix}.Tuple._entry")
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
                if not check_type_recursive(tv, v)[0]:
                    return False, f"{type_err_prefix}Dict._value", f"{k} is not of type {tv}"
                if not check_type_recursive(tk, k)[0]:
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

    success, path, msg = check_type_recursive(expected_type, value)
    return success, f"{path} - {msg}"


T = TypeVar('T')


def type_checking(func: T) -> T:
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

                error_on_fail(check_type(annotation, value), f"Parameter[{i}] {name} has wrong type", error_type=TypeError)

        result = func(*args, **kwargs)

        if signature.return_annotation is not inspect.Parameter.empty:
            error_on_fail(check_type(signature.return_annotation, result), f"Return value has wrong type", error_type=TypeError)

        return result

    return wrapped_func





def recursive_foreach_file(root: Path, func_foreach_file: Callable[[Path], None], func_recurse_directory: Callable[[Path], bool] = None, follow_symlinks: bool = False):
    files: List[Path] = [root]

    if func_recurse_directory is None:
        func_recurse_directory = lambda x: True

    while len(files) > 0:
        file = files.pop()

        if file.is_symlink() and not follow_symlinks:
            continue

        if file.is_symlink() and follow_symlinks:
            file = file.resolve()
            files.append(file)
            continue

        if file.is_dir() and func_recurse_directory(file):
            for child in file.iterdir():
                files.append(child)
            continue

        if file.is_dir() and not func_recurse_directory(file):
            continue

        if file.is_file():
            func_foreach_file(file)
            continue

        raise ValueError(f"Unknown file type {file}")


def deepcopy_dict_remove_private(obj: dict) -> dict:
    data = {}

    for k, v in obj.items():
        if k.startswith("_"):
            continue
        if isinstance(v, dict):
            data[k] = deepcopy_dict_remove_private(v)
        else:
            data[k] = copy.deepcopy(v)

    return data

