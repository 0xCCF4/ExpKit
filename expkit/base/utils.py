import copy
from pathlib import Path
from typing import Type, Union, get_args, get_origin, Dict, Tuple, Optional, List, Callable

StatusError = Tuple[bool, Optional[str]]


def is_optional(field: Type) -> bool:
    return get_origin(field) is Union and type(None) in get_args(field)


def check_dict_types(type_definitions: Dict[str, Type], values: Dict[str, any]) -> StatusError:
    for k, t in type_definitions.items():
        v = values.get(k, None)
        if v is None and not is_optional(t):
            return False, f'Missing required field {k}'
        if not isinstance(v, t):
            return False, f'Field {k} has wrong type {type(v)} instead of {t}'
    return True, None


def error_on_fail(status: StatusError, msg: str, error_type=ValueError, error_status=False) -> StatusError:
    code, nested_msg = status
    if code == error_status:
        raise error_type(f"{msg} {nested_msg}")
    return status


def error_on_fail_any(status: List[StatusError], msg: str, error_type=ValueError, error_status=False) -> List[StatusError]:
    for s in status:
        error_on_fail(s, msg, error_type, error_status)
    return status


def check_type(expected_type: Type, value: any) -> StatusError:
    if value is None and not is_optional(expected_type):
        return False, 'Value is None'
    if not isinstance(value, expected_type):
        return False, f'Value has wrong type {type(value)} instead of {expected_type}'
    return True, None


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


class FinishedDeserialization():
    def finish_deserialization(self):
        """Called after all fields have been set. Can be called multiple times."""
        pass
