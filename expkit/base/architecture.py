from enum import IntFlag
import sys, platform
from typing import List, TypeVar, Generic, Optional, Iterator, Union, Dict


class Architecture(IntFlag):
    UNKNOWN = 0
    NONE = UNKNOWN

    i386 = 1
    AMD64 = 2
    ARM = 4
    ARM64 = 8

    BIT32 = i386 | ARM
    BIT64 = AMD64 | ARM64

    ALL = BIT32 | BIT64

    @staticmethod
    def get_architecture() -> "Architecture":
        cpu = platform.machine()
        if cpu == "x86_64":
            return Architecture.AMD64
        elif cpu == "i386":
            return Architecture.i386
        elif cpu == "armv7l":
            return Architecture.ARM
        elif cpu == "aarch64":
            return Architecture.ARM64
        else:
            raise RuntimeError(f"Unsupported architecture {cpu}")

    def is_single(self) -> bool:
        return self.value.bit_count() == 1

    def is_union(self) -> bool:
        return self.value.bit_count() > 1

    def __contains__(self, item: Union["Architecture", any]):
        if isinstance(item, Architecture):
            if item.is_single():
                return (self.value & item.value) != 0
            else:
                value = Architecture.highest_architecture_bitvalue()
                while value != 0:
                    if (item.value & value) != 0 and (self.value & value) == 0:
                        return False
                    value >>= 1
                return True
        else:
            return super().__contains__(item)

    @staticmethod
    def highest_architecture_bitvalue():
        count = 0
        last_value = 0
        for architecture in Architecture:
            if architecture.is_single():
                value = architecture.value
                assert value > last_value, "Architecture values must be distinct and sorted in ascending order"
                count += 1
                last_value = value
        return last_value

    def get_architectures(self) -> List["Architecture"]:
        return [value for value in Architecture if value in self and value.is_single()]


class Platform(IntFlag):

    WINDOWS = 1
    LINUX = 2
    MACOS = 4

    UNKNOWN = 0
    NONE = UNKNOWN

    ALL = WINDOWS | LINUX | MACOS

    @staticmethod
    def get_system_platform() -> "Platform":
        if sys.platform.startswith('win'):
            return Platform.WINDOWS
        elif sys.platform.startswith('linux'):
            return Platform.LINUX
        elif sys.platform.startswith('darwin'):
            return Platform.MACOS
        else:
            return Platform.ALL

    def supporting_architectures(self) -> List[Architecture]:
        if self.WINDOWS:
            return [Architecture.i386, Architecture.AMD64]
        elif self.LINUX:
            return [Architecture.i386, Architecture.AMD64, Architecture.ARM, Architecture.ARM64]
        elif self.MACOS:
            return [Architecture.AMD64]
        else:
            return []

    def __contains__(self, item: Union["Platform", Architecture, any]) -> bool:
        if isinstance(item, Platform):
            if item.is_single():
                return (self.value & item.value) != 0
            else:
                value = Platform.highest_platform_bitvalue()
                while value != 0:
                    if (item.value & value) != 0 and (self.value & value) == 0:
                        return False
                    value >>= 1
                return True
        elif isinstance(item, Architecture):
            return item in self.supporting_architectures()
        else:
            return super().__contains__(item)


    @staticmethod
    def get_platform_from_name(name: str) -> "Platform":
        name = name.lower()
        for value in Platform:
            if value.name.lower() == name:
                return value

        return Platform.UNKNOWN

    @staticmethod
    def highest_platform_bitvalue():
        count = 0
        last_value = 0
        for platform in Platform:
            if platform.is_single():
                value = platform.value
                assert value > last_value, "Platform values must be distinct and sorted in ascending order"
                count += 1
                last_value = value
        return last_value

    def is_single(self) -> bool:
        return self.value.bit_count() == 1

    def is_union(self) -> bool:
        return self.value.bit_count() > 1

    def get_platforms(self) -> List["Platform"]:
        return [value for value in Platform if value in self and value.is_single()]


class _PAMeta(type):
    def __getattr__(cls, item):
        result = _PLATFORM_ARCHITECTURES.get(item, None)
        if result is None:
            raise AttributeError(f"PlatformArchitecture has no attribute {item}")
        return result


class TargetPlatform(metaclass=_PAMeta):
    def __init__(self, platform: Platform, architecture: Architecture):

        self.__initial_platform = platform
        self.__initial_architecture = architecture

        self._pairs = []

        for p in platform.get_platforms():
            for a in architecture.get_architectures():
                if a in p:
                    self._pairs.append((p, a))

    def merge(self, other: "TargetPlatform") -> "TargetPlatform":
        return TargetPlatform(self.__initial_platform | other.__initial_platform, self.__initial_architecture | other.__initial_architecture)

    def intersection(self, other: "TargetPlatform") -> "TargetPlatform":
        return TargetPlatform(self.__initial_platform & other.__initial_platform, self.__initial_architecture & other.__initial_architecture)

    def is_empty(self):
        return len(self._pairs) == 0

    def __iter__(self):
        return iter(self._pairs)

    def __len__(self):
        return len(self._pairs)

    def __getitem__(self, index):
        return self._pairs[index]

    def __contains__(self, item):
        return item in self._pairs

    def __repr__(self):
        return f"{self.__class__.__name__}({self._pairs})"

    def __str__(self):
        return f"{self.__class__.__name__}({self._pairs})"

    def __eq__(self, other: "TargetPlatform"):
        if isinstance(other, TargetPlatform):
            return set(self._pairs) == set(other._pairs)
        else:
            return super().__eq__(other)

    @staticmethod
    def get_default_values() -> Dict[str, "TargetPlatform"]:
        return _PLATFORM_ARCHITECTURES


_PLATFORM_ARCHITECTURES = {
    "NONE": TargetPlatform(Platform.NONE, Architecture.NONE),
    "ALL": TargetPlatform(Platform.ALL, Architecture.ALL),
    "*": TargetPlatform(Platform.ALL, Architecture.ALL),
    "BIT32": TargetPlatform(Platform.ALL, Architecture.BIT32),
    "BIT64": TargetPlatform(Platform.ALL, Architecture.BIT64),
    "WINDOWS": TargetPlatform(Platform.WINDOWS, Architecture.ALL),
    "LINUX": TargetPlatform(Platform.LINUX, Architecture.ALL),
    "LINUX32": TargetPlatform(Platform.LINUX, Architecture.BIT32),
    "LINUX64": TargetPlatform(Platform.LINUX, Architecture.BIT64),
    "MACOS": TargetPlatform(Platform.MACOS, Architecture.ALL),
    "MACOS64": TargetPlatform(Platform.MACOS, Architecture.BIT64),
    "WINDOWS32": TargetPlatform(Platform.WINDOWS, Architecture.BIT32),
    "WINDOWS64": TargetPlatform(Platform.WINDOWS, Architecture.BIT64)
}


# T = TypeVar('T')
#
#
# class PlatformDict(Generic[T]):
#     def __init__(self):
#         self._data: List[List[T]] = []
#
#         self.clear()
#
#     def add(self, platform: Platform, value: T):
#         self._data.append([platform.value, value])
#
#     def get(self, platform: Platform) -> List[T]:
#         return self._data[platform.value]
#
#     def get_one(self, platform: Platform) -> Optional[T]:
#         lst = self.get(platform)
#         if len(lst) == 0:
#             return None
#         else:
#             return lst[0]
#
#     def has_platform(self, platform: Platform) -> bool:
#         return self.get_one(platform) is not None
#
#     def remove_all(self, platform: Platform):
#         self._data.remove(self._data[platform.value])
#
#     def remove(self, item: T) -> bool:
#         for p in self._data:
#             if item in p:
#                 p.remove(item)
#                 return True
#         return False
#
#     def clear(self):
#         self._data.clear()
#         for _ in range(Platform.highest_platform_bitvalue() + 1):
#             self._data.append([])
#
#     def __str__(self) -> str:
#         return str(self._data)
#
#     def __repr__(self) -> str:
#         return str(self._data)
#
#     def __contains__(self, item: T) -> bool:
#         for p in self._data:
#             if item in p:
#                 return True
#         return False
#
#     def __iter__(self) -> Iterator[T]:
#         for platform in self._data:
#             for item in platform:
#                 yield item
