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

