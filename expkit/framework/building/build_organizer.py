import threading
from typing import Optional, Dict, List, Tuple, Callable

import networkx as nx

from expkit.base.architecture import Platform, Architecture, TargetPlatform
from expkit.base.group.base import GroupTemplate
from expkit.base.logger import get_logger
from expkit.base.payload import Payload, PayloadType
from expkit.base.utils.type_checking import type_guard
from expkit.framework.building.artifact_build_organizer import ArtifactBuildOrganizer
from expkit.framework.building.build_job import BuildJob
from expkit.framework.parser import RootElement, GroupElement, ArtifactElement


LOGGER = get_logger(__name__)


class BuildOrganizer:
    class BuildCallback:
        def __init__(self):
            self.called: bool = False
            self.callbacks: List[Callable[["BuildJob"], None]] = []
    
    @type_guard
    def __init__(self, config: RootElement):
        self.config = config
        self.__initialized = False
        self.__lock = threading.RLock()
        self.graph = nx.DiGraph()

        self.artifact_build_pipeline: Dict[str, ArtifactBuildOrganizer] = {}

        self.target_jobs: Dict[BuildJob, "BuildOrganizer.BuildCallback"] = {}
        self.open_jobs: List[BuildJob] = []

    def initialize(self):
        with self.__lock:
            assert not self.__initialized, "BuildOrganizer can only be initialized once."
            self.__initialized = True

            for artifact in self.config.build_order:
                self.artifact_build_pipeline[artifact.artifact_name] = ArtifactBuildOrganizer(artifact, self.artifact_build_pipeline)

            for artifact in self.artifact_build_pipeline.values():
                artifact.initialize()

            # all artifact pipelines initialized, we can now join the build jobs together

            jobs = []

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
                        raise ValueError(f"Could not find suitable dependency ({payload_type.name}, {artifact.artifact_name}, {platform.name}, {architecture.name}) for {job}")

            for job in jobs:
                for dep in job.dependencies:
                    if job not in dep.dependants:
                        dep.dependants.append(job)

            self.graph = nx.DiGraph()
            self.graph.add_nodes_from(jobs)

            for job in jobs:
                for child in job.children:
                    self.graph.add_edge(job, child, type="parent")
                for dep in job.dependencies:
                    self.graph.add_edge(dep, job, type="dependency")

            for source in [x for x in self.graph.nodes if nx.in_degree(x) == 0]:
                self.open_jobs.append(source)

            # Debug draw graph
            # for job in jobs:
            #     if job.parent is None and len(job.children) == 0:
            #         self.graph.remove_node(job)
            # nx.draw_circular(self.graph, with_labels=True, font_size=1.5, node_size=10)
            # plt.savefig("/tmp/graph.pdf")

    def build(self, artifact_name: str, platform: Platform, architecture: Architecture, payload_type: PayloadType, callback: Optional[Callable[[BuildJob], None]] = None):
        final_callback = None

        with self.__lock:
            assert self.__initialized, "BuildOrganizer must be initialized before calling build()."

            artifact = self.config.artifacts.get(artifact_name, None)
            if artifact is None:
                raise ValueError(f"Artifact '{artifact_name}' is not defined in the configuration.")

            if callback is None:
                def callback(job: BuildJob):
                    LOGGER.info(f"Finished building {job}. No callback registered.")

            artifact_build = self.artifact_build_pipeline.get(artifact_name, None)
            if artifact_build is None:
                raise ValueError(f"Artifact '{artifact_name}' build pipeline not found.")

            target_job = artifact_build.get_output_job(platform, architecture, payload_type)
            if target_job is None:
                raise ValueError(f"Could not find suitable output job for ({payload_type.name}, {platform.name}, {architecture.name})")

            if target_job in self.target_jobs:
                build_callback = self.target_jobs[target_job]
            else:
                self.target_jobs[target_job] = (build_callback := BuildOrganizer.BuildCallback())

            if build_callback.called:
                final_callback = callback

            build_callback.callbacks.append(callback)

        if final_callback is not None:
            final_callback(target_job)

    def notify_job_complete(self, job: BuildJob):
        pass

    def __iter__(self):
        pass


