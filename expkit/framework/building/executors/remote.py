import math
from pathlib import Path
from typing import List

from expkit.base.logger import get_logger
from expkit.base.payload import Payload
from expkit.base.utils.sanitze import sanitize_file_name
from expkit.framework.building.build_job import BuildJob
from expkit.framework.building.executors.local import LocalBuildExecutor
from expkit.framework.parsers.workers import WorkerConfig

LOGGER = get_logger(__name__)


#todo
class RemoteBuildExecutor(LocalBuildExecutor):
    def __init__(self, config: WorkerConfig, temp_directory: Path):
        super().__init__(temp_directory)
        self.config = config

    def get_build_directory(self, job: BuildJob):
        number = f"{job.definition.group_index}".zfill(math.floor(math.log10(len(job.definition.parent.groups)))+1)
        return self.temp_directory / "remote" / sanitize_file_name(job.definition.parent.artifact_name) / f"{number}-{sanitize_file_name(job.group.name)}"

    def __local_execute_job(self, job: BuildJob, deps: List[Payload]) -> Payload:
        with job.lock:
            # todo call remote worker
            payload = job.group.execute(job.parent.job_result,
                                        deps,
                                        job.target_type,
                                        job.target_platform,
                                        job.target_architecture,
                                        job.definition.get_config(),
                                        self.get_build_directory(job))

            return payload
