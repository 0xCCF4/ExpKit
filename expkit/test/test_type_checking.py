import inspect
from typing import Union, Optional, List, Dict

import pytest

from expkit.base.utils.type_checking import check_type, type_guard, get_caller_frame


def test_types():
    assert check_type("", str)[0]
    assert check_type("", Union[int, bool, str])[0]
    assert check_type(None, Optional[List[str]])[0]
    assert check_type({}, Dict[int, str])[0]
    assert check_type({2: "abc", 4: "qq", 8: "33"}, Dict[int, str])[0]

    assert not check_type(66, str)[0]
    assert not check_type(6.9, Union[int, bool, str])[0]
    assert not check_type(("1", "3"), Optional[List[str]])[0]
    assert not check_type({3: "33", 3.9: "44"}, Dict[int, str])[0]
    assert not check_type({2: "abc", 4: "qq", "55": "ww"}, Dict[int, str])[0]

    assert check_type("", type(any))[0]
    assert check_type(55, type(any))[0]


@type_guard
def helper(e: bool, a: List[Dict[int, bool]], *, b: Optional["str"] = None, **kwargs) -> Union[int, str]:
    if e:
        return 1
    else:
        return 3.93


def test_func_decorator():
    helper(True, [{2: True}, {4: False}])
    helper(True, [{2: True}, {4: False}], b="")
    helper(True, [{2: True}, {4: False}], b=None)
    helper(True, [{2: True}, {4: False}], b=None, c=55)
    helper(True, [{2: True}, {4: False}], b=None, c=55, d="")
    helper(True, [{2: True}, {4: False}], b=None, c=55, d="")

    helper(True, [{2: True}, {4: False}], b=None, c=55, d="")


    with pytest.raises(TypeError):
        helper(False, [{2: True}, {4: False}], b=3)

    with pytest.raises(TypeError):
        helper(False, [{2: True}, {4: False}], b="")
    with pytest.raises(TypeError):
        helper(False, [{2: True}, {4: False}], b=None)
    with pytest.raises(TypeError):
        helper(False, [{2: True}, {4: False}], b=None, c=55)
    with pytest.raises(TypeError):
        helper(False, [{2: True}, {4: False}], b=None, c=55, d="")


def test_getcaller_frame():
    assert inspect.currentframe() == get_caller_frame()