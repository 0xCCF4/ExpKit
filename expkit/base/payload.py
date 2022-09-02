from enum import IntEnum, auto

from expkit.base.architecture import TargetPlatform
from expkit.base.utils.type_checking import type_guard


class PayloadType(IntEnum):
    UNKNOWN = auto()
    EMPTY = auto()

    # Compiled executable and shared libraries
    DOTNET_DLL = auto()
    DOTNET_EXE = auto()

    NATIVE_STATIC_EXE = auto()
    NATIVE_DYNAMIC_EXE = auto()

    NATIVE_STATIC_DLL = auto()
    NATIVE_DYNAMIC_DLL = auto()

    NATIVE_SHELLCODE = auto()

    # Source code and other files
    POWERSHELL_SCRIPT = auto()
    CSHARP_PROJECT = auto()

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

    def is_project(self):
        return self.name.endswith("_PROJECT")

    def is_empty(self):
        return self == PayloadType.EMPTY

    def is_file(self):
        return not self.is_project() and not self.is_empty()

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name


class Payload():
    @type_guard
    def __init__(self, type: PayloadType, platform: TargetPlatform, content: bytes, meta: dict = None):
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
        return self.meta
