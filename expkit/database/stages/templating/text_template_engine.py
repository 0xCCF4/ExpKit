from typing import List, Optional, Dict

from expkit.base.architecture import TargetPlatform
from expkit.base.logger import get_logger
from expkit.base.payload import Payload, PayloadType
from expkit.base.stage.base import StageTemplate
from expkit.base.stage.context import StageContext
from expkit.base.task.base import TaskTemplate
from expkit.base.utils.files import recursive_foreach_file
from expkit.database.tasks.general.utils.tar_folder import TarTaskOutput
from expkit.framework.database import register_stage, TaskDatabase, auto_stage_group

LOGGER = get_logger(__name__)


@auto_stage_group("TEMPLATE_ENGINE", "A template engine that can be used to modify and generate source code.")
@register_stage
class TextTemplateEngine(StageTemplate):
    def __init__(self):
        super().__init__(
            name="stages.templating.text_template_engine",
            description="A stage that uses a text template engine to transform strings.",
            platform=TargetPlatform.ALL,
            required_parameters={
                "TPL_VARIABLES": Dict[str, str],
                "TPL_EXTENSIONS": Optional[List[str]],
            }
        )

        self.tasks.append(TaskDatabase.get_instance().get_task("tasks.general.utils.untar_folder"))
        self.tasks.append(TaskDatabase.get_instance().get_task("tasks.obfuscation.csharp.string_transform_template"))
        self.tasks.append(TaskDatabase.get_instance().get_task("tasks.general.utils.tar_folder"))

    def execute_task(self, context: StageContext, index: int, task: TaskTemplate):
        task_parameters = {}

        if task.name == "tasks.general.utils.untar_folder":
            task_parameters["folder"] = context.build_directory
            task_parameters["tarfile"] = context.initial_payload.get_content()

            status = task.execute(task_parameters, context.build_directory, self)

            if not status.success:
                raise Exception("Failed to untar folder.")

        elif task.name == "task.obfuscation.csharp.string_transform_template":
            extensions = context.parameters.get("TPL_EXTENSIONS", None)
            if extensions is None:
                extensions = ["cs", "csproj", "sln", "c", "cpp", "h", "hpp", "txt", "md", "json", "xml", "yml", "yaml", "asm", "s", "ps1", "psm1"]
            else:
                LOGGER.debug("Using custom file extension list for template engine:")
                for extension in extensions:
                    LOGGER.debug(f" - .{extension}")

            files = []
            recursive_foreach_file(context.build_directory, lambda f: files.append(f))
            transform_params = []

            LOGGER.debug("Running template engine on files:")
            for file in files:
                if (len(file.suffix) == 0 and "" in extensions) or file.suffix[1:] in extensions:
                    LOGGER.debug(f" - {file}")
                    transform_params.append((file, file))
                else:
                    LOGGER.debug(f" - [SKIP] {file}")

            task_parameters["files"] = transform_params
            task_parameters["replacements"] = context.parameters.get("TPL_VARIABLES", {})

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
        return PayloadType.get_all_types(include_empty=False)

    def get_output_payload_type(self, input: PayloadType, dependencies: List[PayloadType]) -> List[PayloadType]:
        return [input] if input.is_file() or input.is_project() else []
