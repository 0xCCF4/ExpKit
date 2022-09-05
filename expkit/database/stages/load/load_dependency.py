from typing import List

from expkit.base.architecture import TargetPlatform
from expkit.base.payload import Payload, PayloadType
from expkit.base.stage.base import StageTemplate
from expkit.base.stage.context import StageContext
from expkit.base.task.base import StageTaskTemplate
from expkit.framework.database import register_stage, auto_stage_group


@auto_stage_group("LOAD_DEPENDENCY", "Loads another artifact as dependency.")
@register_stage
class LoadDependency(StageTemplate):
    def __init__(self):
        super().__init__(
            name="stages.load.load_dependency",
            description="Loads another artifact as dependency.",
            platform=TargetPlatform.ALL,
            required_parameters={}
        )

    def prepare_build(self, context: StageContext):
        super().prepare_build(context)

        dependencies = context.get("dependencies")
        if len(dependencies) != 1:
            raise Exception("This stage requires exactly one dependency.")

        dependency = context.get("dependencies")[0]
        if dependency.payload_type != context.get("target_format"):
            raise Exception(f"Dependency {dependency} is not of the required type {context.get('target_format')}.")

    def execute_task(self, context: StageContext, index: int, task: StageTaskTemplate):
        raise Exception("This stage does not have any tasks.")

    def finish_build(self, context: StageContext) -> Payload:
        dependency = context.get("dependencies")[0]
        return dependency.copy()

    def get_supported_input_payload_types(self) -> List[PayloadType]:
        return [PayloadType.EMPTY]

    def get_output_payload_type(self, input: PayloadType, dependencies: List[PayloadType]) -> List[PayloadType]:
        if input != PayloadType.EMPTY:
            return []
        if len(dependencies) == 1:
            return [dependencies[0]]
        return []

    def get_supported_dependency_types(self) -> List[List[PayloadType]]:
        result = []
        for pt in PayloadType.get_all_types():
            result.append([pt])
        return result
