import threading
from typing import Dict, List, Tuple, Optional

from expkit.base.architecture import Platform, Architecture, TargetPlatform
from expkit.base.payload import Payload, PayloadType
from expkit.base.utils.type_checking import type_guard
from expkit.framework.building.build_job import BuildJob, JobState
from expkit.framework.parser import RootElement, ArtifactElement


class ArtifactBuildOrganizer:
    #@type_guard
    def __init__(self, config: ArtifactElement, build_organizer: "BuildOrganizer"):
        self.config = config
        self.__initialized = False
        self.__lock = threading.RLock()

        self.build_organizer = build_organizer

        self.empty_root_nodes: Dict[Tuple[Platform, Architecture], BuildJob] = {}
        self.finish_nodes: List[BuildJob] = []

    @property
    def lock(self) -> threading.RLock:
        return self.__lock

    def initialize(self):
        with self.__lock:
            assert not self.__initialized, "BuildOrganizer can only be initialized once."
            self.__initialized = True

            callback = self.build_organizer.notify_job_update

            for target_platform, target_architecture in TargetPlatform.ALL:
                empty_root = BuildJob(None, None, PayloadType.EMPTY, target_platform, target_architecture, callback)
                empty_root.mark_running(notify=False)
                self.empty_root_nodes[(target_platform, target_architecture)] = empty_root
                empty_root.mark_complete(Payload(PayloadType.EMPTY, bytes(), target_platform, target_architecture, None), notify=False)

                last_jobs_set = [empty_root]
                new_last_jobs_set = []

                for group_definition in self.config.groups:
                    group = group_definition.template
                    assert group is not None

                    for group_cache_entry in group.get_supported_platforms():
                        if group_cache_entry.platform == target_platform and group_cache_entry.architecture == target_architecture:
                            group_input = group_cache_entry.input_type
                            group_output = group_cache_entry.output_type
                            dependency_types = group_cache_entry.dependencies
                            dependency_artifacts = group_definition.dependencies

                            if len(dependency_types) == len(dependency_artifacts):
                                for last_job in last_jobs_set:
                                    if last_job.target_type == group_input:
                                        job = BuildJob(group_definition, group, group_output, target_platform, target_architecture, callback)
                                        job.parent = last_job

                                        for dep_type, (dep_art, dep_plat, dep_arch) in zip(dependency_types, dependency_artifacts):
                                            job.required_deps.append((dep_type, dep_art, dep_plat, dep_arch))

                                        new_last_jobs_set.append(job)

                    last_jobs_set = new_last_jobs_set
                    new_last_jobs_set = []

                self.finish_nodes.extend(last_jobs_set)

            # Resolve children
            queue = self.finish_nodes.copy()
            while len(queue) > 0:
                job = queue.pop(0)
                parent = job.parent

                if parent is not None:
                    if job not in parent.children:
                        parent.children.append(job)
                        if parent not in queue:
                            queue.append(parent)

    # def has_more(self, platform: Optional[Platform] = None, architecture: Optional[Architecture] = None, include_running: bool = False) -> bool:
    #     assert platform.is_single()
    #     assert architecture.is_single()
    #     with self.__lock:
    #         assert self.__initialized, "BuildOrganizer must be initialized before use."
    #
    #         for fjob in self.finish_nodes:
    #             if platform is not None and fjob.target_platform != platform:
    #                 continue
    #             if architecture is not None and fjob.target_architecture != architecture:
    #                 continue
    #             if fjob.state.is_pending():
    #                 return True
    #             if fjob.state.is_running() and include_running:
    #                 return True
    #
    #     return False

    def get_output(self, platform: Platform, architecture: Architecture, payload_type: PayloadType) -> Optional[Payload]:
        with self.__lock:
            assert self.__initialized, "BuildOrganizer must be initialized before use."

            fjob = self.get_output_job(platform, architecture, payload_type)
            if fjob is None:
                raise ValueError(f"Could not find output job for {platform} {architecture} {payload_type}")

            if fjob.state == JobState.SUCCESS:
                if fjob.job_result is not None:
                    return fjob.job_result

            return None

    def get_output_job(self, platform: Platform, architecture: Architecture, payload_type: PayloadType) -> Optional[BuildJob]:
        with self.__lock:
            assert self.__initialized, "BuildOrganizer must be initialized before use."

            for fjob in self.finish_nodes:
                if fjob.target_platform == platform and fjob.target_architecture == architecture and fjob.target_type == payload_type:
                    return fjob

            return None
