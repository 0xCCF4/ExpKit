import os
from functools import wraps
from pathlib import Path
from typing import List, Optional

from expkit.base.architecture import TargetPlatform
from expkit.base.payload import Payload, PayloadType
from expkit.base.stage.base import StageTemplate
from expkit.base.stage.context import StageContext
from expkit.base.stage.wrong_output_type_exception import SkipStageExecution
from expkit.base.task.base import TaskTemplate
from expkit.database.tasks.general.utils.tar_folder import TarTaskOutput
from expkit.framework.database import register_stage, TaskDatabase, auto_stage_group


@auto_stage_group("LOAD_FOLDER", "Loads a project folder from disk.")
@register_stage
class LoadProject(StageTemplate):
    def __init__(self):
        super().__init__(
            name="stages.load.load_project",
            description="Loads a project from disk.",
            platform=TargetPlatform.ALL,
            required_parameters=[
                ("LOAD_FOLDER_PATH", str, "Path to the folder to load."),
                ("LOAD_TARGET_FORMAT", str, "Target payload format to load the project as."),
            ]
        )

        self.add_task("tasks.general.utils.copy_template_folder")
        self.add_task("tasks.general.utils.tar_folder")

    def prepare_build(self, context: StageContext):
        super().prepare_build(context)

        target_format = PayloadType.get_type_from_name(context.parameters["LOAD_TARGET_FORMAT"])
        if target_format == PayloadType.UNKNOWN:
            raise Exception(f"Unknown target format {context.parameters['LOAD_TARGET_FORMAT']}")

        if not target_format.is_project():
            raise Exception(f"Target format {target_format} is not a PROJECT format.")

        if target_format != context.output_type:
            self._skip_execution(context, f"Can not produce {context.output_type} as {target_format} was requested as output.")

        context.set("target_format", target_format)

    def execute_task(self, context: StageContext, index: int, task: TaskTemplate):
        task_parameters = {}

        if task.name == "tasks.general.utils.copy_template_folder":
            task_parameters["source"] = source = Path(context.parameters["LOAD_FOLDER_PATH"])
            task_parameters["target"] = target = Path(context.build_directory)

            if not source.exists() or not source.is_dir():
                raise Exception(f"Source folder {source} does not exist or is not a folder.")
            if target.exists() or not target.is_dir():
                raise Exception(f"Target folder {target} already exists or is not a folder.")
            if task_parameters["source"] == task_parameters["target"]:
                raise Exception("Source and target must be different.")

            status = task.execute(task_parameters, context.build_directory, self)

            if not status.success:
                raise Exception(f"Failed to copy template folder {source} to {target}")

        elif task.name == "tasks.general.utils.tar_folder":
            task_parameters["folder"] = context.build_directory

            status = task.execute(task_parameters, context.build_directory, self)

            if not status.success:
                raise Exception("Failed to tar folder.")

            assert isinstance(status, TarTaskOutput)

            context.set("output", status.data)

    def finish_build(self, context: StageContext) -> Payload:
        assert context.get("output") is not None

        return context.initial_payload.copy(
            type=context.get("target_format"),
            content=context.get("output"))

    def _skip_execution(self, context, reason: str):
        raise SkipStageExecution(self, context, reason)

    def get_supported_input_payload_types(self) -> List[PayloadType]:
        return [PayloadType.EMPTY]

    def get_output_payload_type(self, input: PayloadType, dependencies: List[PayloadType]) -> List[PayloadType]:
        return [] if input != PayloadType.EMPTY else PayloadType.get_all_project_types()
