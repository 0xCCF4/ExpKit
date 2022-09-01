from typing import Tuple, Optional, Type, List

StatusError = Tuple[bool, Optional[str]]


def error_on_fail(status: StatusError, msg: str, error_type:Type[Exception]=ValueError, error_status=False) -> StatusError:
    code, nested_msg = status
    if code == error_status:
        raise error_type(f"{msg} {nested_msg}")
    return status


def error_on_fail_any(status: List[StatusError], msg: str, error_type=ValueError, error_status=False) -> List[StatusError]:
    for s in status:
        error_on_fail(s, msg, error_type, error_status)
    return status
