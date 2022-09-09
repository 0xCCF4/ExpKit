import os
import threading
from pathlib import Path
from typing import Dict, Optional, Type, TypeVar, Generic, List, Callable, Union, Tuple

from expkit.base.command.base import CommandTemplate, CommandArgumentCount
from expkit.base.group.base import GroupTemplate
from expkit.base.logger import get_logger
from importlib import import_module

from expkit.base.stage.base import StageTemplate
from expkit.base.task.base import TaskTemplate
from expkit.base.utils.files import recursive_foreach_file

LOGGER = get_logger(__name__)

T = TypeVar("T")
class RegisterDecoratorHelper(Generic[T]):
    def __init__(self):
        self._registered: List[T] = []
        self._lock = threading.Lock()
        self.finished = False

    def finalize(self, func: Callable[[T], any]):
        with self._lock:
            if self.finished and len(self._registered) > 0:
                raise RuntimeError("RegisterAnnotationHelper is finalized")
            for task in self._registered:
                func(task)
            self.finished = True

    def register(self, obj: T):
        with self._lock:
            if self.finished:
                LOGGER.error(f"Unable to register {obj} as the database initialization is completed")
            else:
                self._registered.append(obj)

__helper_tasks: RegisterDecoratorHelper[Tuple[Type[TaskTemplate], tuple, dict]] = RegisterDecoratorHelper()
__helper_stages: RegisterDecoratorHelper[Tuple[Type[StageTemplate], tuple, dict]] = RegisterDecoratorHelper()
__helper_groups: RegisterDecoratorHelper[Tuple[Type[GroupTemplate], tuple, dict]] = RegisterDecoratorHelper()
__helper_auto_groups: RegisterDecoratorHelper[Tuple[str, str, Optional[str]]] = RegisterDecoratorHelper()
__helper_commands: RegisterDecoratorHelper[Tuple[Type[CommandTemplate], tuple, dict]] = RegisterDecoratorHelper()


def _register_obj(type: int, *cargs, **kwargs):
    args = cargs

    def decorator(obj: Type[Union[TaskTemplate, StageTemplate, GroupTemplate, CommandTemplate]]):
        if type==1: # task
            assert issubclass(obj, TaskTemplate)
            __helper_tasks.register((obj, args, kwargs))
            setattr(obj, "__auto_register__", (args, kwargs))
        elif type==2: # stage
            assert issubclass(obj, StageTemplate)
            __helper_stages.register((obj, args, kwargs))
            setattr(obj, "__auto_register__", (args, kwargs))
        elif type==3: # group
            assert issubclass(obj, GroupTemplate)
            __helper_groups.register((obj, args, kwargs))
            setattr(obj, "__auto_register__", (args, kwargs))
        elif type==4: # auto group
            assert issubclass(obj, StageTemplate)
            autoconf = getattr(obj, "__auto_register__", None)

            if autoconf is None or len(autoconf) != 2:
                raise RuntimeError(f"Stage {obj} was not registered with @register_stage")

            stage_name = obj(*autoconf[0], **autoconf[1]).name

            if not (1 <= len(args) <= 2 and len(kwargs) == 0):
                raise ValueError("Auto-grouping requires a group name and optional description")

            group_name = args[0]
            description = None

            if len(args) == 2:
                description = args[1]

            if not isinstance(group_name, str) or (description is not None and not isinstance(description, str)):
                raise ValueError("Auto-grouping requires a string arguments")

            __helper_auto_groups.register((group_name, stage_name, description))
        elif type==5: # command
            assert issubclass(obj, CommandTemplate)
            __helper_commands.register((obj, args, kwargs))
        else:
            raise TypeError(f"Unable to register {obj} as it is not a StageTaskTemplate, StageTemplate, StageTemplateGroup, CommandTemplate or AutoGroup")

        return obj

    if len(cargs) == 1 and len(kwargs) == 0 and callable(cargs[0]):
        # no parameters for decorator

        if type==4:
            raise TypeError("Auto-grouping requires a group name")

        args = ()
        return decorator(cargs[0])
    else:
        # arguments provided for decorator
        return decorator


def register_task(*cargs, **kwargs):
    return _register_obj(1, *cargs, **kwargs)


def register_stage(*cargs, **kwargs):
    return _register_obj(2, *cargs, **kwargs)


def register_stage_group(*cargs, **kwargs):
    return _register_obj(3, *cargs, **kwargs)


def auto_stage_group(*cargs, **kwargs):
    return _register_obj(4, *cargs, **kwargs)


def register_command(*cargs, **kwargs):
    return _register_obj(5, *cargs, **kwargs)


def auto_discover_databases(directory: Path, module_prefix: str = "expkit."):
    LOGGER.debug(f"Discovering database entries in {directory}")

    files = []
    recursive_foreach_file(directory, lambda f: files.append(f), lambda d: d.name != "__pycache__" and not d.name.startswith("test"))

    if len(module_prefix.strip()) > 0 and not module_prefix.endswith("."):
        module_prefix += "."
    for file in files:
        if file.name.endswith(".py") and not file.name.startswith("test"):
            module_name = f"{module_prefix}{str(file.relative_to(directory)).replace(os.sep, '.')[:-3]}"
            try:
                import_module(module_name)  # Calls to register_* will be executed
            except ImportError as e:
                LOGGER.error(f" - error importing module {module_name}")
                LOGGER.error(e)
                continue


def build_databases():
    __helper_tasks.finalize(lambda entry: TaskDatabase.get_instance().add_task(entry[0](*entry[1], **entry[2])))
    __helper_stages.finalize(lambda entry: StageDatabase.get_instance().add_stage(entry[0](*entry[1], **entry[2])))
    __helper_groups.finalize(lambda entry: GroupDatabase.get_instance().add_group(entry[0](*entry[1], **entry[2])))

    auto_group_data_raw = []
    __helper_auto_groups.finalize(auto_group_data_raw.append)

    auto_group_data: Dict[str, List[Tuple[str, Optional[str]]]] = {}

    for group, stage, description in auto_group_data_raw:
        if group not in auto_group_data:
            auto_group_data[group] = []
        if stage in auto_group_data[group]:
            LOGGER.warning(f"Stage {stage} is already in group {group}")
        auto_group_data[group].append((stage, description))

    for group, data in auto_group_data.items():
        group_obj = GroupDatabase.get_instance().get_group(group)

        if group_obj is None:
            descriptions = [description for _, description in data]
            descriptions = sorted(set(filter(lambda d: d is not None, descriptions)))
            if len(descriptions) == 0:
                raise ValueError(f"Group {group} does not exist and cannot be auto-created as no descriptions are provided")
            if len(descriptions) > 1:
                LOGGER.error("Error auto-creating group {group}: multiple descriptions provided")
                for d in descriptions:
                    LOGGER.error(f" - {d}")
                raise ValueError(f"Group {group} does not exist and cannot be auto-created as multiple different descriptions are provided")

            description = descriptions[0]
            group_obj = GroupDatabase.get_instance().add_group(GroupTemplate(group, description))

        LOGGER.debug(f"Auto-grouping {group}")

        for stage, _ in data:
            stage_obj = StageDatabase.get_instance().get_stage(stage)

            if stage_obj is None:
                raise ValueError(f"Stage {stage} does not exist and cannot be auto-grouped")

            LOGGER.debug(f" - grouping {stage}")
            group_obj.add_stage(stage_obj)

    commands_buffer: List[CommandTemplate] = []
    __helper_commands.finalize(lambda entry: commands_buffer.append(entry[0](*entry[1], **entry[2])))
    root_cmd = CommandDatabase.get_instance()

    all_cmds = [root_cmd]

    iteration = 0
    while len(commands_buffer) > 0 and iteration < 3:
        index = 0
        while index < len(commands_buffer):
            cmd = commands_buffer[index]
            found_parent = None
            for parent in all_cmds:
                if parent.can_be_attached_as_child(cmd):
                    found_parent = parent
            if found_parent is not None:
                found_parent.add_command(cmd)
                all_cmds.append(cmd)
                del commands_buffer[index]
                iteration = 0
            else:
                index += 1
        iteration += 1

    cmd_tree = root_cmd.get_children(recursive=True, order_child_first=True)

    LOGGER.debug("Discovered command tree:")
    for cmd in cmd_tree:
        level = len(cmd.name.split("."))
        prepend = " " * (level - 1) * 2
        name = "<ROOT>" if cmd == root_cmd else cmd.name.split(".")[-1]

        LOGGER.debug(f"{prepend}+- {name}")

    if len(commands_buffer) > 0:
        LOGGER.error("Unable to attach the following commands to the command tree:")
        for cmd in commands_buffer:
            LOGGER.error(f" - {cmd.name}")
        raise ValueError("Unable to attach some commands to the command tree")

    for cmd in root_cmd.get_children(recursive=True, order_child_first=False):
        cmd.finalize()
    root_cmd.finalize()


class TaskDatabase():
    def __init__(self):
        self.tasks: Dict[str, TaskTemplate] = {}
        LOGGER.debug("Created task database")

    def add_task(self, task: TaskTemplate) -> TaskTemplate:
        assert task.name == task.name.lower(), "Only lower case task names are allowed"
        if task.name in self.tasks:
            raise ValueError(f"Task with name {task.name} already exists in the database")
        LOGGER.debug(f" - registered task {task.name}")
        self.tasks[task.name.lower()] = task

        return task

    def get_task(self, name: str) -> Optional[TaskTemplate]:
        return self.tasks.get(name, None)

    def __len__(self):
        return len(self.tasks)

    __instance: 'TaskDatabase' = None
    @staticmethod
    def get_instance() -> 'TaskDatabase':
        if TaskDatabase.__instance is None:
            TaskDatabase.__instance = TaskDatabase()
        return TaskDatabase.__instance


class StageDatabase():
    def __init__(self):
        self.stages: Dict[str, StageTemplate] = {}
        LOGGER.debug("Created stage database")

    def add_stage(self, stage: StageTemplate) -> StageTemplate:
        assert stage.name == stage.name.lower(), "Only lower case stage names are allowed"
        if stage.name in self.stages:
            raise ValueError(f"Stage with name {stage.name} already exists in the database")
        LOGGER.debug(f" - registered stage {stage.name}")
        self.stages[stage.name.lower()] = stage

        return stage

    def get_stage(self, name: str) -> Optional[StageTemplate]:
        return self.stages.get(name, None)

    def __len__(self):
        return len(self.stages)

    __instance: 'StageDatabase' = None
    @staticmethod
    def get_instance() -> 'StageDatabase':
        if StageDatabase.__instance is None:
            StageDatabase.__instance = StageDatabase()
        return StageDatabase.__instance


class GroupDatabase():
    def __init__(self):
        self.groups: Dict[str, GroupTemplate] = {}
        LOGGER.debug("Created stage group database")

    def add_group(self, group: GroupTemplate) -> GroupTemplate:
        assert group.name == group.name.upper(), "Only upper case stage group names are allowed"
        if group.name in self.groups:
            raise ValueError(f"Stage group with name {group.name} already exists in the database")
        LOGGER.debug(f" - registered stage group {group.name}")
        self.groups[group.name.upper()] = group

        return group

    def get_group(self, name: str) -> Optional[GroupTemplate]:
        return self.groups.get(name, None)

    def __len__(self):
        return len(self.groups)

    __instance: 'GroupDatabase' = None
    @staticmethod
    def get_instance() -> 'GroupDatabase':
        if GroupDatabase.__instance is None:
            GroupDatabase.__instance = GroupDatabase()
        return GroupDatabase.__instance


class CommandDatabase():
    def __init__(self):
        LOGGER.debug("Created command database")

    __instance: CommandTemplate = None
    @staticmethod
    def get_instance() -> CommandTemplate:
        if CommandDatabase.__instance is None:
            CommandDatabase.__instance = CommandTemplate("", CommandArgumentCount(0,0), "<ROOT>")
        return CommandDatabase.__instance
