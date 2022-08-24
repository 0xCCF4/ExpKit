from enum import IntFlag
import sys
from typing import List, TypeVar, Generic, Optional, Iterator


class Platform(IntFlag):
    WINDOWS = 1
    LINUX = 2
    MACOS = 4

    UNKNOWN = 0
    NONE = UNKNOWN

    ALL = WINDOWS | LINUX | MACOS

    @staticmethod
    def get_platform() -> "Platform":
        if sys.platform.startswith('win'):
            return Platform.WINDOWS
        elif sys.platform.startswith('linux'):
            return Platform.LINUX
        elif sys.platform.startswith('darwin'):
            return Platform.MACOS
        else:
            return Platform.ALL

    def get_platform_name(self) -> str:
        if self.WINDOWS:
            return 'Windows'
        elif self.LINUX:
            return 'Linux'
        elif self.MACOS:
            return 'MacOS'
        else:
            return 'Unknown'

    def __str__(self) -> str:
        return self.get_platform_name()

    def __repr__(self) -> str:
        return self.get_platform_name()

    def __contains__(self, item: "Platform") -> bool:
        return (self.value & item.value) != 0

    @staticmethod
    def get_platform_from_name(name: str) -> "Platform":
        name = name.lower()
        for value in Platform:
            if value.name.lower() == name:
                return value

        return Platform.UNKNOWN

    @staticmethod
    def get_platforms() -> List["Platform"]:
        return [value for value in Platform if value != Platform.UNKNOWN and value.value.bit_count() == 1]

    @staticmethod
    def highest_platform_bitvalue():
        count = 0
        last_value = 0
        for platform in Platform.get_platforms():
            value = platform.value
            assert value > last_value, "Platform values must be distinct and sorted in ascending order"
            count += 1
            last_value = value
        return last_value

    @property
    def value(self) -> int:
        return super(self).value()


T = TypeVar('T')


class PlatformDict(Generic[T]):
    def __init__(self):
        self._data: List[List[T]] = []

        self.clear()

    def add(self, platform: Platform, value: T):
        self._data.append([platform.value, value])

    def get(self, platform: Platform) -> List[T]:
        return self._data[platform.value]

    def get_one(self, platform: Platform) -> Optional[T]:
        lst = self.get(platform)
        if len(lst) == 0:
            return None
        else:
            return lst[0]

    def has_platform(self, platform: Platform) -> bool:
        return self.get_one(platform) is not None

    def remove_all(self, platform: Platform):
        self._data.remove(self._data[platform.value])

    def remove(self, item: T) -> bool:
        for p in self._data:
            if item in p:
                p.remove(item)
                return True
        return False

    def clear(self):
        self._data.clear()
        for _ in range(Platform.highest_platform_bitvalue() + 1):
            self._data.append([])

    def __str__(self) -> str:
        return str(self._data)

    def __repr__(self) -> str:
        return str(self._data)

    def __contains__(self, item: T) -> bool:
        for p in self._data:
            if item in p:
                return True
        return False

    def __iter__(self) -> Iterator[T]:
        for platform in self._data:
            for item in platform:
                yield item
