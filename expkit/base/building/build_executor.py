from expkit.base.logger import get_logger
from expkit.framework.building.build_job import BuildJob

LOGGER = get_logger(__name__)


class BuildExecutor:
    def initialize(self):
        pass

    def shutdown(self):
        pass

    def execute_job(self, job: BuildJob):
        raise NotImplementedError("BuildExecutor.execute_job() must be implemented by subclasses.")

    def get_build_directory(self, job: BuildJob):
        raise RuntimeError("TODO: Implement BuildExecutor.get_build_directory()")
