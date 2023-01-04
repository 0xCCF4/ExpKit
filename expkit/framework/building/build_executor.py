from expkit.base.architecture import Platform
from expkit.base.logger import get_logger
from expkit.base.stage.wrong_output_type_exception import SkipStageExecution
from expkit.framework.building.build_job import BuildJob, JobState

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


class LocalBuildExecutor(BuildExecutor):
    def __local_execute_job(self, job: BuildJob):
        with job.lock:
            assert job.parent is not None, "Job must have a parent job."
            assert job.parent.state == JobState.SUCCESS, "Parent job must be successful."
            assert job.parent.job_result is not None, "Parent job must have a result."

            assert len(job.required_deps) == len(job.dependencies), "Job must have all dependencies resolved."
            deps = []

            for (dep_type, _, _, _), dep in zip(job.required_deps, job.dependencies):
                assert dep_type == dep.target_type, "Dependency type must match."
                assert dep.state == JobState.SUCCESS, "Dependency must be successful."
                assert dep.job_result is not None, "Dependency must have a result."
                deps.append(dep.job_result)

            job.mark_running()

            try:
                payload = job.group.execute(job.parent.job_result,
                                            deps,
                                            job.target_type,
                                            job.target_platform,
                                            job.target_architecture,
                                            job.definition.get_config(),
                                            self.get_build_directory(job))

                if payload is None:
                    raise SkipStageExecution("Stage returned None.")

                job.mark_complete(payload)
            except SkipStageExecution as e:
                job.mark_skipped()
                LOGGER.info(f"Skipping job {job} because {e.message}")
            except Exception as e:
                job.mark_error()
                LOGGER.error(f"Job {job} failed with exception: {e.with_traceback(e.__traceback__)}")

    def execute_job(self, job: BuildJob):
        with job.lock:
            if not job.state.is_pending():
                raise RuntimeError(f"Job is not pending. Job is in state {job.state.name}.")

            if job.target_platform in [Platform.DUMMY, Platform.get_system_platform()]:
                self.__local_execute_job(job)
            else:
                raise ValueError(
                    f"BuildExecutor does not support building for platform {job.target_platform.name} ({job.target_architecture.name}).")
