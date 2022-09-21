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


class BuildJob:
    def __init__(self,
                 definition: Optional[GroupElement],
                 group: Optional[GroupTemplate],
                 target_type: PayloadType,
                 target_platform: Platform,
                 target_architecture: Architecture,
                 callback: Callable[["BuildJob"], None]):
        self.definition = definition
        self.group = group
        self.callback = callback

        self.target_type = target_type
        self.target_platform = target_platform
        self.target_architecture = target_architecture

        self.parent: Optional[BuildJob] = None
        self.required_deps: List[Tuple[PayloadType, ArtifactElement, Platform, Architecture]] = []
        self.children: List[BuildJob] = []

        self.state: JobState = JobState.PENDING
        self.job_result: Optional[Payload] = None

    @type_guard
    def mark_complete(self, job_output: Payload):
        assert self.state == JobState.RUNNING
        self.job_result = job_output
        self.state = JobState.SUCCESS
        self.callback(self)

    def mark_error(self):
        assert self.state == JobState.RUNNING
        self.state = JobState.FAILED
        self.callback(self)

    def mark_skipped(self):
        assert self.state == JobState.RUNNING
        self.state = JobState.SKIPPED
        self.callback(self)

    def __str__(self):
        return f"BuildJob({self.target_platform.name}, {self.target_architecture.name}, {self.target_type}, {self.state.name}, {None if self.definition is None else self.definition.group_name})"

    def __repr__(self):
        return str(self)