from enum import Enum

from expkit.base.platform import Platform


class PayloadType(Enum):
    UNKNOWN = 0

    # Compiled executable and shared libraries
    DOTNET_DLL = 1
    DOTNET_EXE = 2

    NATIVE_STATIC_EXE = 3
    NATIVE_DYNAMIC_EXE = 4

    NATIVE_STATIC_DLL = 5
    NATIVE_DYNAMIC_DLL = 6

    NATIVE_SHELLCODE = 7

    # Source code and other files
    POWERSHELL_SCRIPT = 8
    CSHARP_PROJECT = 9

    @staticmethod
    def get_type_from_name(name: str) -> "PayloadType":
        name = name.lower()
        for value in PayloadType:
            if value.name.lower() == name:
                return value

        return PayloadType.UNKNOWN

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name


class Payload():
    def __init__(self, type: PayloadType, platform: Platform, content: bytes, meta: dict = None):
        self.type = type
        self.platform = platform
        self.data = {
            "content": content,
            "meta": meta if meta is not None else {}
        }

    def __str__(self) -> str:
        return self.type.name

    def get_content(self) -> bytes:
        return self.data["content"]

    def get_content_base64(self) -> str:
        return self.data["content"].decode('base64')

    def get_content_hex(self) -> str:
        return self.data["content"].hex()

    def get_meta(self) -> dict:
        return self.data["meta"]
