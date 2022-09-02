import io
import re
import shutil
import tarfile
from pathlib import Path
from typing import Optional, List

from expkit.base.architecture import TargetPlatform
from expkit.base.logger import get_logger
from expkit.base.stage.base import StageTemplate
from expkit.base.task.base import TaskOutput
from expkit.database.tasks.general.utils.abstract_foreach_file_task import AbstractForeachFileTask
from expkit.framework.database import register_task

LOGGER = get_logger(__name__)


class TarTaskOutput(TaskOutput):
    def __init__(self, success: bool, data: Optional[bytes] = None):
        super().__init__(success)
        self.data = data


@register_task
class TarFolderTask(AbstractForeachFileTask):
    def __init__(self):
        super().__init__(
            name="tasks.general.utils.tar_folder",
            description="Creates an in memory tar files from a folder on disk.",
            platform=TargetPlatform.ALL,
            required_parameters={
                "folder": Path,
            }
        )
        self._tarfile_raw = None
        self._tarfile = None

    def _get_origin_folder(self, parameters: dict, stage: StageTemplate) -> Optional[Path]:
        return parameters["folder"]

    def _prepare_task(self, parameters: dict, build_directory: Path, stage: StageTemplate) -> TaskOutput:
        LOGGER.debug(f"Taring folder file from folder {self._get_origin_folder(parameters, stage)}")
        return super()._prepare_task(parameters, build_directory, stage)

    def _process_file(self, file: Path, origin: Path, build_directory: Path, parameters: dict, stage: StageTemplate) -> TaskOutput:
        assert self._lock.locked()

        rel_file = file.relative_to(self._get_origin_folder(parameters, stage))

        content = file.read_bytes()
        tf = tarfile.TarInfo(str(rel_file))
        tf.size = len(content)

        self._tarfile.addfile(tf, io.BytesIO(content))

        return TaskOutput(success=True)

    def execute(self, parameters: dict, build_directory: Path, stage: StageTemplate) -> TaskOutput:
        with self._lock:
            self._tarfile_raw = io.BytesIO()
            with tarfile.open(fileobj=self._tarfile_raw, mode="w|") as self._tarfile:
                status = super().execute(parameters, build_directory, stage)

            self._tarfile_raw.seek(0)

            if not status.success:
                return status

            return TarTaskOutput(success=True, data=self._tarfile_raw.read())
