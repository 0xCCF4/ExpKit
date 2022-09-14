import threading
from enum import auto, IntEnum
from typing import Optional, Dict, List

import networkx as nx

from expkit.base.architecture import Platform, Architecture, TargetPlatform
from expkit.base.group.base import GroupTemplate
from expkit.base.payload import Payload, PayloadType
from expkit.base.utils.type_checking import type_guard
from expkit.framework.parser import RootElement, GroupElement


class JobState(IntEnum):
    PENDING = auto()
    RUNNING = auto()
    FAILED = auto()
    SKIPPED = auto()
    SUCCESS = auto()


class BuildJob:
    @type_guard
    def __init__(self, definition: Optional[GroupElement], group: Optional[GroupTemplate], target_type: PayloadType, target_platform: Platform, target_architecture: Architecture, organizer: 'BuildOrganizer'):
        self.definition = definition
        self.group = group
        self.organizer = organizer

        self.target_type = target_type
        self.target_platform = target_platform
        self.target_architecture = target_architecture

        self.parent: Optional[BuildJob] = None
        self.dependencies: List[BuildJob] = []
        self.children: List[BuildJob] = []

        self.state: JobState = JobState.PENDING
        self.job_result: Optional[Payload] = None

    @type_guard
    def mark_complete(self, job_output: Payload):
        assert self.state == JobState.RUNNING
        self.job_result = job_output
        self.state = JobState.SUCCESS
        self.organizer.notify_job_complete(self)

    def mark_error(self):
        assert self.state == JobState.RUNNING
        self.state = JobState.FAILED
        self.organizer.notify_job_complete(self)

    def mark_skipped(self):
        assert self.state == JobState.RUNNING
        self.state = JobState.SKIPPED
        self.organizer.notify_job_complete(self)


class BuildOrganizer:
    @type_guard
    def __init__(self, config: RootElement, target_platform: TargetPlatform):
        self.config = config
        self.__initialized = False
        self.__lock = threading.RLock()

        self.target_platform = target_platform

        self.graph_shadow_root: BuildJob = BuildJob(None, None, Platform.UNKNOWN, Architecture.UNKNOWN, self)

        self.artifact_final_jobs: Dict[str, List[BuildJob]] = {}

    def initialize(self):
        with self.__lock:
            assert not self.__initialized, "BuildOrganizer can only be initialized once."
            self.__initialized = True

            self.graph_shadow_root.mark_complete(Payload(PayloadType.UNKNOWN, bytes()))

            # # Add root nodes
            # for target_platform, target_architecture in self.target_platform:
            #     self.graph_shadow_root.children.append(empty_root := BuildJob(None, None, PayloadType.EMPTY, target_platform, target_architecture, self))
            #     empty_root.mark_complete(Payload(PayloadType.EMPTY, bytes()))
            #
            #     # Add stage nodes
            #     for artifact in self.config.build_order:
            #         last_jobs_set = [empty_root]
            #
            #         for group_definition in artifact.groups:
            #             group = group_definition.template
            #             assert group is not None
            #
            #             for group_cache_entry in group.get_supported_platforms():
            #                 if group_cache_entry.platform == target_platform and group_cache_entry.architecture == target_architecture:
            #                     group_input = group_cache_entry.input_type
            #                     group_output = group_cache_entry.output_type
            #                     dependencies = group_cache_entry.dependencies
            #
            #                     for last_job in last_jobs_set:
            #                         if last_job.target_type == group_input:
            #                             job = BuildJob(group, group_output, target_platform, target_architecture, self)
            #
            #                             dependency_artifact_names = [d.artifact_name for d in group_definition.dependencies]
            #                             assert len(dependency_artifact_names) == len(dependencies)
            #                             for dependency in dependencies:
            #                                 dependency_outputs = self.artifact_final_jobs[dependency.artifact_name]
            #
            #
            #
            #                             job.parent = last_job
            #                             last_job.children.append(job)




                                # group_cache_entry.dependencies



    def has_more_jobs(self) -> bool:
        with self.__lock:
            assert self.__initialized, "BuildOrganizer must be initialized before use."

            return True

    def get_next_job(self, concurrent_jobs: bool = True) -> Optional[BuildJob]:
        with self.__lock:
            assert self.__initialized, "BuildOrganizer must be initialized before use."


            pass

        return None

    @type_guard
    def notify_job_complete(self, job: BuildJob):
        with self.__lock:
            assert self.__initialized, "BuildOrganizer must be initialized before use."
            if job == self.graph_shadow_root or job in self.graph_shadow_root.children:
                return

            pass

    def get_output(self, name: str) -> Optional[Payload]:
        with self.__lock:
            assert self.__initialized, "BuildOrganizer must be initialized before use."

            if name not in self.artifact_payloads:
                raise KeyError(f"Artifact '{name}' does not exist.")

            return self.artifact_payloads[name]
