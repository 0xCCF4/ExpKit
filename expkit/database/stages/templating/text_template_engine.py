from typing import List, Optional, Dict

from expkit.base.architecture import TargetPlatform
from expkit.base.payload import Payload, PayloadType
from expkit.base.stage.base import StageTemplate
from expkit.base.stage.context import StageContext
from expkit.base.task.base import StageTaskTemplate
from expkit.base.utils.files import recursive_foreach_file
from expkit.database.tasks.general.utils.tar_folder import TarTaskOutput
from expkit.framework.database import register_stage, TaskDatabase


@register_stage
class CSharpObfuscationStage(StageTemplate):
    def __init__(self):
        super().__init__(
            name="stages.templating.text_template_engine",
            description="A stage that uses a text template engine to transform strings.",
            platform=TargetPlatform.ALL,
            required_parameters={
                "TPL_VARIABLES": Dict[str, str]
            }
        )

        self.tasks.append(TaskDatabase.get_instance().get_task("tasks.general.utils.untar_folder"))
        self.tasks.append(TaskDatabase.get_instance().get_task("task.obfuscation.csharp.string_transform_template"))
        self.tasks.append(TaskDatabase.get_instance().get_task("tasks.general.utils.tar_folder"))

    def execute_task(self, context: StageContext, index: int, task: StageTaskTemplate):
        task_parameters = {}

        if task.name == "tasks.general.utils.untar_folder":
            task_parameters["folder"] = context.build_directory
            task_parameters["tarfile"] = context.initial_payload.get_content()

            status = task.execute(task_parameters, context.build_directory, self)

            if not status.success:
                raise Exception("Failed to untar folder.")

        elif task.name == "task.obfuscation.csharp.string_transform_template":


            # TODO STUFF


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
        # TODO
        return [PayloadType.CSHARP_PROJECT]

    def get_output_payload_type(self, input: PayloadType, dependencies: List[PayloadType]) -> List[PayloadType]:
        # TODO
        return [PayloadType.CSHARP_PROJECT] if input == PayloadType.CSHARP_PROJECT else []