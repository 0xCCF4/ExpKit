import copy
import json
from base64 import b64encode
from enum import IntEnum, auto
from json import JSONEncoder
from typing import Optional

from expkit.base.architecture import TargetPlatform
from expkit.base.utils.type_checking import type_guard


class PayloadType(IntEnum):
    # Special types
    UNKNOWN = auto()
    EMPTY = auto()

    # Project types
    CSHARP_PROJECT = auto()

    # Scripts

    # Compiled binaries
    DOTNET_BINARY = auto()

    @staticmethod
    @type_guard
    def get_type_from_name(name: str) -> "PayloadType":
        name = name.lower()
        for value in PayloadType:
            if value.name.lower() == name:
                return value

        return PayloadType.UNKNOWN

    @staticmethod
    def get_all_project_types():
        return [value for value in PayloadType if value.is_project()]

    @staticmethod
    def get_all_types(include_empty=True):
        return [value for value in PayloadType if value != PayloadType.UNKNOWN and (include_empty or value != PayloadType.EMPTY)]

    @staticmethod
    def get_all_file_types():
        return [value for value in PayloadType if value.is_file()]

    def is_project(self):
        return self.name.endswith("_PROJECT")

    def is_empty(self):
        return self == PayloadType.EMPTY

    def is_file(self):
        return not self.is_project() and not self.is_empty()

    def is_binary(self):
        return "BINARY" in self.name

    def get_description(self) -> str:
        if self == PayloadType.EMPTY:
            return "Empty payload"
        elif self == PayloadType.DOTNET_BINARY:
            return "Compiled .NET binary"
        elif self == PayloadType.CSHARP_PROJECT:
            return "C# project folder"
        else:
            return "Unknown payload type"

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name


class Payload():
    @type_guard
    def __init__(self, type: PayloadType, content: bytes, meta: dict = None):
        self.type = type
        self.content = content
        self.meta = meta if meta is not None else {}


    def __str__(self) -> str:
        return self.type.name

    def get_content(self) -> bytes:
        return self.content

    def get_content_base64(self) -> str:
        return self.content.decode('base64')

    def get_content_hex(self) -> str:
        return self.content.hex()

    def get_meta(self) -> dict:
        return copy.deepcopy(self.meta)

    @type_guard
    def copy(self, type: Optional[PayloadType] = None, content: Optional[bytes] = None, meta: Optional[dict] = None):
        payload = Payload(self.type, self.content, copy.deepcopy(self.meta))

        if type is not None:
            payload.type = type
        if content is not None:
            payload.content = content
        if meta is not None:
            payload.meta = meta

        return payload

    def get_json_metadata(self) -> str:
        meta = self.get_meta()

        class Base64Encoder(JSONEncoder):
            def default(self, o):
                if isinstance(o, bytes):
                    return b64encode(o).decode()
                return JSONEncoder.default(self, o)

        return json.dumps(meta, cls=Base64Encoder)

