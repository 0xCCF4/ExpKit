import copy
import inspect
from pathlib import Path


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


def bit_count(value: int) -> int:
    assert value >= 0
    count = 0
    while value > 0:
        if (value & 1) != 0:
            count += 1
        value = value >> 1
    return count
