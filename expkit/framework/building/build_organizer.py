import threading
from enum import auto, IntEnum
from typing import Optional, Dict, List, Tuple

import matplotlib
import networkx as nx

from expkit.base.architecture import Platform, Architecture, TargetPlatform
from expkit.base.group.base import GroupTemplate
from expkit.base.payload import Payload, PayloadType
from expkit.base.utils.type_checking import type_guard
from expkit.framework.building.artifact_build_organizer import ArtifactBuildOrganizer
from expkit.framework.building.build_job import BuildJob
from expkit.framework.parser import RootElement, GroupElement, ArtifactElement
import matplotlib.pyplot as plt #todo remove


class BuildOrganizer:
    @type_guard
    def __init__(self, config: RootElement):
        self.config = config
        self.__initialized = False
        self.__lock = threading.RLock()
        self.graph = nx.DiGraph()

        self.artifact_build_pipeline: Dict[str, ArtifactBuildOrganizer] = {}
        self.build_proxies: Dict[Tuple[str, Platform, Architecture], "BuildOrganizer.BuildProxy"] = {}

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
                    pass

            self.graph = nx.DiGraph()
            self.graph.add_nodes_from(jobs)

            for job in jobs:
                for child in job.children:
                    self.graph.add_edge(job, child)
                for dep in job.dependencies:
                    self.graph.add_edge(dep, job, type="dependency")

            # todo remove
            for job in jobs:
                if job.parent is None and len(job.children) == 0:
                    self.graph.remove_node(job)
            nx.draw_circular(self.graph, with_labels=True, font_size=1.5, node_size=10)
            plt.savefig("/tmp/graph.pdf")
            pass

    class BuildProxy():
        def __init__(self, build_organizer: "BuildOrganizer", artifact: ArtifactElement, platform: Platform, architecture: Architecture):
            self.artifact_config = artifact
            self.platform = platform
            self.architecture = architecture
            self.build_organizer = build_organizer
            self.artifact_organizer = build_organizer.artifact_build_pipeline[artifact.artifact_name]
            assert self.artifact_organizer is not None

            self.__lock = threading.RLock()

        def has_next(self, include_running: bool = False) -> bool:
            with self.__lock:
                return self.artifact_organizer.has_more(self.platform, self.architecture, include_running=include_running)

        def get_outputs(self) -> List[Payload]:
            with self.__lock:
                return self.artifact_organizer.get_outputs(self.platform, self.architecture)

        def get_next(self) -> Optional[BuildJob]:
            pass

    def build(self, artifact_name: str, platform: Platform, architecture: Architecture) -> "BuildProxy":
        with self.__lock:
            assert self.__initialized, "BuildOrganizer must be initialized before calling build()."

            artifact = self.config.artifacts.get(artifact_name, None)
            if artifact is None:
                raise ValueError(f"Artifact '{artifact_name}' is not defined in the configuration.")

            if (artifact_name, platform, architecture) not in self.build_proxies:
                self.build_proxies[(artifact_name, platform, architecture)] = self.BuildProxy(self, artifact, platform, architecture)

            return self.build_proxies[(artifact_name, platform, architecture)]
