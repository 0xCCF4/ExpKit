import threading
from typing import Optional, Dict, List

import networkx as nx

from expkit.base.payload import Payload
from expkit.base.utils.type_checking import type_guard
from expkit.framework.parser import RootElement, StageElement


class BuildJob:
    @type_guard
    def __init__(self, stage: StageElement, organizer: 'BuildOrganizer'):
        self.stage = stage
        self.organizer = organizer
        self.output: Optional[Payload] = None
        self.success = False

    @type_guard
    def mark_complete(self, job_output: Payload):
        self.output = job_output
        self.success = True
        self.organizer._mark_job_complete(self)

    def mark_error(self):
        self.organizer._mark_job_complete(self)


class BuildOrganizer:
    @type_guard
    def __init__(self, config: RootElement):
        self.config = config
        self.__initialized = False
        self.__lock = threading.RLock()

        self._payload_graph = nx.DiGraph()
        self.artifact_payloads: Dict[str, Payload] = {}

        self._finished_jobs: List[BuildJob] = []
        self._queued_jobs: List[BuildJob] = []

    def initialize(self):
        with self.__lock:
            assert not self.__initialized, "BuildOrganizer can only be initialized once."
            self.__initialized = True



    def has_more_jobs(self) -> bool:
        with self.__lock:
            assert self.__initialized, "BuildOrganizer must be initialized before use."

            return True

    def get_next_job(self, concurrent_jobs: bool = True) -> Optional[BuildJob]:
        with self.__lock:
            assert self.__initialized, "BuildOrganizer must be initialized before use."

            if len(self._queued_jobs) > 0 and not concurrent_jobs:
                return None

            pass

        return None

    def _mark_job_complete(self, job: BuildJob):
        with self.__lock:
            assert self.__initialized, "BuildOrganizer must be initialized before use."

            pass

    def get_output(self, name: str) -> Optional[Payload]:
        with self.__lock:
            assert self.__initialized, "BuildOrganizer must be initialized before use."

            if name not in self.artifact_payloads:
                raise KeyError(f"Artifact '{name}' does not exist.")

            return self.artifact_payloads[name]
