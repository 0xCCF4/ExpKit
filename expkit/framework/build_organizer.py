import threading
from enum import auto, IntEnum
from typing import Optional, Dict, List

import networkx as nx

from expkit.base.architecture import Platform, Architecture, TargetPlatform
from expkit.base.group.base import GroupTemplate
from expkit.base.payload import Payload, PayloadType
from expkit.base.utils.type_checking import type_guard
from expkit.framework.organizer.artifact_build_organizer import ArtifactBuildOrganizer
from expkit.framework.parser import RootElement, GroupElement


class BuildOrganizer:
    @type_guard
    def __init__(self, config: RootElement):
        self.config = config
        self.__initialized = False
        self.__lock = threading.RLock()

        self.artifact_build_pipeline: Dict[str, ArtifactBuildOrganizer] = {}

    def initialize(self):
        with self.__lock:
            assert not self.__initialized, "BuildOrganizer can only be initialized once."
            self.__initialized = True

            for artifact in self.config.build_order:
                self.artifact_build_pipeline[artifact.artifact_name] = ArtifactBuildOrganizer(artifact, self.artifact_build_pipeline)

            for artifact in self.artifact_build_pipeline.values():
                artifact.initialize()
