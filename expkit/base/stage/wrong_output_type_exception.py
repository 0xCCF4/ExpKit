from expkit.base.stage.base import StageTemplate
from expkit.base.stage.context import StageContext
from expkit.base.utils.type_checking import type_guard


class SkipStageExecution(Exception):
    """Exception raised when the target output-type of a stage can not be produced using the current context."""

    @type_guard
    def __init__(self, stage: StageTemplate, context: StageContext, message: str):
        super().__init__(message)
        self.message = message
        self.context = context
        self.stage = stage
