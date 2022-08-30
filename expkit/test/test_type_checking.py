from typing import Union, Optional, List, Dict

import pytest

from expkit.base.utils import check_type, type_checking


def test_types():
    assert check_type(str, "")[0]
    assert check_type(Union[int, bool, str], "")[0]
    assert check_type(Optional[List[str]], None)[0]
    assert check_type(Dict[int, str], {})[0]
    assert check_type(Dict[int, str], {2: "abc", 4: "qq", 8: "33"})[0]

    assert not check_type(str, 66)[0]
    assert not check_type(Union[int, bool, str], 6.9)[0]
    assert not check_type(Optional[List[str]], ("1", "3"))[0]
    assert not check_type(Dict[int, str], {3: "33", 3.9: "44"})[0]
    assert not check_type(Dict[int, str], {2: "abc", 4: "qq", "55": "ww"})[0]

    assert check_type(type(any), "")[0]
    assert check_type(type(any), 55)[0]


@type_checking
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