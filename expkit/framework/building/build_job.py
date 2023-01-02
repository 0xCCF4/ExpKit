import threading
from datetime import datetime
from enum import IntEnum, auto
from typing import Optional, Callable, List, Tuple

from expkit.base.architecture import Platform, Architecture
from expkit.base.group.base import GroupTemplate
from expkit.base.payload import PayloadType, Payload
from expkit.base.utils.type_checking import type_guard
from expkit.framework.parser import GroupElement, ArtifactElement


class JobState(IntEnum):
    PENDING = auto()

    RUNNING = auto()

    FAILED = auto()
    SKIPPED = auto()
    SUCCESS = auto()

    def is_finished(self) -> bool:
        return self in (JobState.FAILED, JobState.SKIPPED, JobState.SUCCESS)

    def is_running(self) -> bool:
        return self == JobState.RUNNING

    def is_pending(self) -> bool:
        return self == JobState.PENDING

    def is_success(self):
        assert self.is_finished()
        return self == JobState.SUCCESS


class BuildJob:
    def __init__(self,
                 definition: Optional[GroupElement],
                 group: Optional[GroupTemplate],
                 target_type: PayloadType,
                 target_platform: Platform,
                 target_architecture: Architecture,
                 callback: Callable[["BuildJob"], None]):

        assert target_platform is not None and target_platform.is_single()
        assert target_architecture is not None and target_architecture.is_single()

        self.definition = definition
        self.group = group
        self.callback = callback

        self.target_type = target_type
        self.target_platform = target_platform
        self.target_architecture = target_architecture

        self.parent: Optional[BuildJob] = None
        self.children: List[BuildJob] = []
        self.required_deps: List[Tuple[PayloadType, ArtifactElement, Platform, Architecture]] = []
        self.dependencies: List[BuildJob] = []
        self.dependants: List[BuildJob] = []

        self.start_time: Optional[datetime] = None
        self.stop_time: Optional[datetime] = None

        self.__state: JobState = JobState.PENDING
        self.__job_result: Optional[Payload] = None
        self.__lock = threading.RLock()

    @property
    def lock(self) -> threading.RLock:
        return self.__lock

    @property
    def state(self) -> JobState:
        with self.lock:
            return self.__state

    @state.setter
    def state(self, value: JobState):
        assert value is not None and isinstance(value, JobState)
        with self.lock:
            if self.__state == value:
                return

            assert not self.__state.is_pending() or (value.is_running() or value.is_finished()), f"Logic condition: old=PENDING => (new=RUNNING v new=FINISHED) is not valid. old={self.__state.name}, new={value.name}"
            assert not self.__state.is_running() or (value.is_finished()), f"Logic condition: old=RUNNING => new=FINISHED is not valid. old={self.__state.name}, new={value.name}"
            self.__state = value

    @property
    def job_result(self) -> Optional[Payload]:
        with self.lock:
            return self.__job_result

    @job_result.setter
    def job_result(self, value: Optional[Payload]):
        with self.lock:
            self.__job_result = value

    def mark_running(self):
        with self.lock:
            assert self.state == JobState.PENDING

            self.state = JobState.RUNNING
            self.start_time = datetime.now()

    @type_guard
    def mark_complete(self, job_output: Payload):
        with self.lock:
            assert self.state == JobState.RUNNING

            self.job_result = job_output
            self.state = JobState.SUCCESS
            self.stop_time = datetime.now()
            if self.callback:
                self.callback(self)

    def mark_error(self):
        with self.lock:
            assert self.state == JobState.RUNNING

            self.state = JobState.FAILED
            self.stop_time = datetime.now()
            if self.callback:
                self.callback(self)

    def mark_skipped(self):
        with self.lock:
            assert self.state == JobState.RUNNING

            self.state = JobState.SKIPPED
            self.stop_time = datetime.now()
            if self.callback:
                self.callback(self)

    def __str__(self):
        return f"BuildJob({'-' if self.definition is None else self.definition.parent.get_name()}:" \
               f"{self.target_type.name}:{'-' if self.definition is None else self.definition.group_index}," \
               f"{self.target_platform.name}, {self.target_architecture.name}), " \
               f"[{', '.join([d[0].name for d in self.required_deps]) if len(self.required_deps) > 0 else '-'}] -> " \
               f"{self.target_type}, state={self.state.name})"

    def __repr__(self):
        return str(self)

    def can_build(self) -> bool:
        for dep in self.dependencies:
            if not dep.state.is_success():
                return False
        if self.parent is not None and not self.parent.state.is_success():
            return False
        return True

    def build_before(self) -> List["BuildJob"]:
        if self.can_build():
            return []
        else:
            result = []
            for dep in self.dependencies:
                if dep.can_build() and not dep.state.is_finished():
                    result.append(dep)
            return result
