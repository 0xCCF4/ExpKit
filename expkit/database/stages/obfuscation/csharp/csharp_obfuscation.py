from typing import List, Optional

from expkit.base.architecture import TargetPlatform
from expkit.base.payload import Payload, PayloadType
from expkit.base.stage.base import StageTemplate
from expkit.base.stage.context import StageContext
from expkit.base.task.base import TaskTemplate
from expkit.base.utils.files import recursive_foreach_file
from expkit.database.tasks.general.utils.tar_folder import TarTaskOutput
from expkit.framework.database import register_stage, TaskDatabase, auto_stage_group


@auto_stage_group("OBFUSCATE_CSHARP", "Obfuscates CSharp source code to prevent signature detection.")
@register_stage
class CSharpObfuscationStage(StageTemplate):
    def __init__(self):
        super().__init__(
            name="stages.obfuscation.csharp.csharp_obfuscation",
            description="Obfuscates CSharp source code to prevent signature detection.",
            platform=TargetPlatform.ALL,
            required_parameters={
                "OBF_STRING_ENCODING": Optional[str]
            }
        )

        self.add_task("tasks.general.utils.untar_folder")
        self.add_task("tasks.obfuscation.csharp.string_transform_template")
        self.add_task("tasks.general.utils.tar_folder")

        assert len(self.tasks) == 0 or len(self.tasks) == 3

    def execute_task(self, context: StageContext, index: int, task: TaskTemplate):
        task_parameters = {}

        if task.name == "tasks.general.utils.untar_folder":
            task_parameters["folder"] = context.build_directory
            task_parameters["tarfile"] = context.initial_payload.get_content()

            status = task.execute(task_parameters, context.build_directory, self)

            if not status.success:
                raise Exception("Failed to untar folder.")

        elif task.name == "task.obfuscation.csharp.string_transform_template":
            task_parameters["OBF_STRING_ENCODING"] = context.parameters.get("OBF_STRING_ENCODING", None)

            files = []
            recursive_foreach_file(context.build_directory, lambda f: files.append(f))
            transform_params = []

            for file in files:
                if file.suffix == ".cs":
                    transform_params.append((file, file))

            task_parameters["files"] = transform_params

            status = task.execute(task_parameters, context.build_directory, self)

            if not status.success:
                raise Exception("Failed to transform strings.")

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
            type=PayloadType.CSHARP_PROJECT,
            content=context.get("output"))

    def get_supported_input_payload_types(self) -> List[PayloadType]:
        return [PayloadType.CSHARP_PROJECT]

    def get_output_payload_type(self, input: PayloadType, dependencies: List[PayloadType]) -> List[PayloadType]:
        return [PayloadType.CSHARP_PROJECT] if input == PayloadType.CSHARP_PROJECT else []
    