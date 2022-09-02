from pathlib import Path
from typing import Dict

from expkit.base.payload import Payload, PayloadType


class StageContext:
    def __init__(self, initial_payload: Payload, output_type: PayloadType, parameters: dict, build_directory: Path):
        self.initial_payload = initial_payload
        self.output_type = output_type
        self.parameters = parameters
        self.build_directory = build_directory
        self.data: Dict[str, any] = {}

    def get(self, key: str, default: any = None) -> any:
        return self.data.get(key, default)

    def set(self, key: str, value: any):
        self.data[key] = value

    def __delitem__(self, key):
        del self.data[key]

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

    def __contains__(self, key):
        return key in self.data

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)
