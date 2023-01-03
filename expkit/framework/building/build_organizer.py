import threading
from enum import auto, IntEnum
from typing import Dict, List, Tuple, Iterator, Optional

import networkx as nx

from expkit.base.architecture import Platform, Architecture
from expkit.base.logger import get_logger
from expkit.base.utils.type_checking import type_guard
from expkit.framework.building.artifact_build_organizer import ArtifactBuildOrganizer
from expkit.framework.building.build_job import BuildJob
from expkit.framework.parser import RootElement, ArtifactElement


LOGGER = get_logger(__name__)


class JobSchedulingInfo(IntEnum):
    NOT_SCHEDULED = auto()
    BLOCKED_BY_DEPENDENCY = auto()
    READY_TO_BUILD = auto()
    BUILDING = auto()
    FINISHED = auto()


class BuildOrganizer:
    @type_guard
    def __init__(self, config: RootElement):
        self.config = config
        self.__initialized = False
        self.__lock = threading.RLock()
        self.graph = nx.DiGraph()

        self.artifact_build_pipeline: Dict[str, ArtifactBuildOrganizer] = {}
        self.jobs: List[BuildJob] = []

        self.scheduling_info: Dict[BuildJob, JobSchedulingInfo] = {}
        self.queued_jobs: List[BuildJob] = []

    def initialize(self):
        with self.__lock:
            assert not self.__initialized, "BuildOrganizer can only be initialized once."
            self.__initialized = True

            for artifact in self.config.build_order:
                self.artifact_build_pipeline[artifact.artifact_name] = ArtifactBuildOrganizer(artifact, self)

            for artifact in self.artifact_build_pipeline.values():
                artifact.initialize()

            # all artifact pipelines initialized, we can now join the build jobs together

            self.jobs = jobs = []

            for artifact in self.artifact_build_pipeline.values():
                jobs.extend(artifact.empty_root_nodes.values())

            index = 0
            while index < len(jobs):
                job = jobs[index]
                index += 1

                for child in job.children:
                    if child not in jobs:
                        jobs.insert(index, child)
                        assert jobs[index] == child

            for job in jobs:
                for payload_type, artifact, platform, architecture in job.required_deps:
                    artifact_build: ArtifactBuildOrganizer = self.artifact_build_pipeline[artifact.artifact_name]
                    job.dependencies.clear()

                    found = False
                    for finish_job in artifact_build.finish_nodes:
                        if finish_job.target_type == payload_type and finish_job.target_platform == platform and finish_job.target_architecture == architecture:
                            if found:
                                LOGGER.warning(f"Found multiple suitable dependencies for job {job} using ({payload_type.name}, {artifact.artifact_name}, {platform.name}, {architecture.name}).")
                            else:
                                # Check build order
                                try:
                                    target_artifact_index = self.config.build_order.index(job.definition.parent)
                                    dep_artifact_index = self.config.build_order.index(finish_job.definition.parent)
                                except ValueError:
                                    raise ValueError("Artifact not found in build order.")

                                assert target_artifact_index >= 0 and dep_artifact_index >= 0, "Artifact not found in build order."
                                assert target_artifact_index > dep_artifact_index, f"Build order violation: {job} depends on {finish_job}."

                                job.dependencies.append(finish_job)
                                found = True
                    if not found:
                        raise ValueError(
                            f"Could not find suitable dependency ({payload_type.name}, {artifact.artifact_name}, {platform.name}, {architecture.name}) for {job}")

            self.graph = nx.DiGraph()
            self.graph.add_nodes_from(jobs)

            for job in jobs:
                for child in job.children:
                    self.graph.add_edge(job, child, type="parent")
                for dep in job.dependencies:
                    self.graph.add_edge(dep, job, type="dependency")

            for job in jobs:
                self.scheduling_info[job] = JobSchedulingInfo.NOT_SCHEDULED

            for job in jobs:
                self.scheduling_info[job] = JobSchedulingInfo.NOT_SCHEDULED

            # todo add plotting option for dependecy debugging
            #for job in jobs:
            #    if job.parent is None and len(job.children) == 0:
            #        self.graph.remove_node(job)
            #nx.draw_circular(self.graph, with_labels=True, font_size=1.5, node_size=10)
            #plt.savefig("/tmp/graph.pdf")

    def _update_job(self, job: BuildJob, queue_job: bool = False):
        assert job in self.jobs, "Job is not part of the build pipeline."

        with self.__lock:
            result = self.scheduling_info[job]
            info = self.scheduling_info[job]

            if info == JobSchedulingInfo.NOT_SCHEDULED and queue_job:
                # also queue all dependencies

                # assume job is ready to build
                result = JobSchedulingInfo.READY_TO_BUILD

                if job.state.is_finished():
                    result = JobSchedulingInfo.FINISHED
                else:
                    for dep in [job.parent, *job.dependencies]:
                        if dep is None: continue
                        dep_info = self.scheduling_info[dep]

                        if dep_info == JobSchedulingInfo.NOT_SCHEDULED:
                            self._update_job(dep, queue_job=queue_job)
                            dep_info = self.scheduling_info[dep]

                        assert dep_info != JobSchedulingInfo.NOT_SCHEDULED, "Dependency not scheduled."

                        if dep_info == JobSchedulingInfo.BLOCKED_BY_DEPENDENCY:
                            result = JobSchedulingInfo.BLOCKED_BY_DEPENDENCY
                            break
                        elif dep_info == JobSchedulingInfo.BUILDING:
                            result = JobSchedulingInfo.BLOCKED_BY_DEPENDENCY
                            break
                        elif dep_info == JobSchedulingInfo.READY_TO_BUILD:
                            result = JobSchedulingInfo.BLOCKED_BY_DEPENDENCY
                            break
                        elif dep_info == JobSchedulingInfo.FINISHED:
                            assert dep.state.is_finished(), "Dependency finished but not in finished state."
                            if dep.state.is_success():
                                continue # dependency finished successfully, we can continue
                            else:
                                # job state failed or skipped
                                result = JobSchedulingInfo.FINISHED
                                break

            elif info == JobSchedulingInfo.BLOCKED_BY_DEPENDENCY:
                # check if job is still blocked by dependency

                # assume job is ready to build
                result = JobSchedulingInfo.READY_TO_BUILD

                for dep in [job.parent, *job.dependencies]:
                    if dep is None: continue
                    self._update_job(dep, queue_job=queue_job)
                    dep_info = self.scheduling_info[dep]

                    if dep_info == JobSchedulingInfo.FINISHED:
                        assert dep.state.is_finished(), "Dependency finished but not in finished state."
                        if dep.state.is_success():
                            # dependency finished successfully, we can continue
                            continue
                        else:
                            # job state failed or skipped
                            result = JobSchedulingInfo.FINISHED
                            break
                    else:
                        # job is still blocked by dependency
                        result = JobSchedulingInfo.BLOCKED_BY_DEPENDENCY
                        break

            elif info == JobSchedulingInfo.READY_TO_BUILD:
                # job is ready to build - ignore
                pass

            elif info == JobSchedulingInfo.BUILDING:
                # job is building - check state
                if job.state.is_finished():
                    result = JobSchedulingInfo.FINISHED
                else:
                    pass

            elif info == JobSchedulingInfo.FINISHED:
                # job is already finished
                if job in self.queued_jobs:
                    self.queued_jobs.remove(job)
                pass

            else:
                raise Exception(f"Unknown job scheduling info {info.name}")

            # set mew scheduling info
            self.scheduling_info[job] = result

    def queue_job(self, artifact: ArtifactElement, platform: Platform, architecture: Architecture):
        jobs = self.artifact_build_pipeline[artifact.artifact_name].finish_nodes
        target_jobs = []
        for job in jobs:
            if job.target_platform == platform and job.target_architecture == architecture:
                target_jobs.append(job)

        for job in target_jobs:
            assert job in self.jobs, "Job is not part of the build pipeline."

        with self.__lock:
            for job in target_jobs:
                if job in self.queued_jobs:
                    continue

                self.queued_jobs.append(job)
                self._update_job(job, queue_job=True)

        return target_jobs

    def update_job_state(self, job: BuildJob):
        assert job in self.jobs, "Job is not part of the build pipeline."

        with self.__lock:
            self._update_job(job, queue_job=False)

    def open_jobs(self):
        open_jobs = []

        with self.__lock:
            for potential_job, info in self.scheduling_info.items():
                if info != JobSchedulingInfo.FINISHED and info != JobSchedulingInfo.NOT_SCHEDULED\
                        and not potential_job.state.is_finished():
                    open_jobs.append(potential_job)

        return open_jobs

    def building_jobs(self):
        building_jobs = []

        with self.__lock:
            for potential_job, info in self.scheduling_info.items():
                if info == JobSchedulingInfo.BUILDING and not potential_job.state.is_finished():
                    building_jobs.append(potential_job)

        return building_jobs

    def build(self) -> Iterator[Optional[BuildJob]]:
        while True:
            # find next job to build
            jobs = []

            with self.__lock:
                for potential_job, info in self.scheduling_info.items():
                    if info == JobSchedulingInfo.READY_TO_BUILD:
                        self.scheduling_info[potential_job] = JobSchedulingInfo.BUILDING
                        jobs.append(potential_job)

            if len(jobs) <= 0 and len(self.open_jobs()) <= 0:
                # no job to build left
                break
            elif len(jobs) <= 0:
                # no job to build right now
                yield None
            else:
                # issue build requests
                for job in jobs:
                    yield job
