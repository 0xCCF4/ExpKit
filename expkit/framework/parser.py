import copy
import threading
from typing import Optional, List, Union, Dict, Tuple
import networkx as nx

from expkit.base.architecture import TargetPlatform, Platform, Architecture
from expkit.base.group.base import GroupTemplate
from expkit.base.logger import get_logger
from expkit.base.utils.base import error_on_fail
from expkit.base.utils.data import deepcopy_dict_remove_private
from expkit.base.utils.type_checking import check_type, type_guard, check_dict_types
from expkit.framework.database import GroupDatabase

LOGGER = get_logger(__name__)


class ParserBlock:
    def __init__(self, parent: 'ParserBlock' = None):
        self.parent = parent
        self.config = {}
        self._config_cache = None

    def __str__(self):
        return f"{self.get_name()}"

    def __repr__(self):
        return f"{self.get_block_type()}({self.get_name()})"

    def get_block_type(self) -> str:
        raise NotImplementedError()

    def get_name(self):
        raise NotImplementedError()

    def get_config(self) -> dict:
        if not self._config_cache:
            self._config_cache = {}

            if self.get_block_type() == "root":
                self._config_cache = copy.deepcopy(self.config)
            elif self.get_block_type() == "artifact" or self.get_block_type() == "group":
                self._config_cache = copy.deepcopy(self.parent.get_config()) # use parent config as template
                for key, value in self.config.items(): # override with current config
                    self._config_cache[key] = copy.deepcopy(value)
            else:
                raise RuntimeError(f"Unknown block type: {self.get_block_type()}")

        return self._config_cache

    @staticmethod
    def platform_from_json(data: dict) -> TargetPlatform:
        error_on_fail(check_type(data, List[str]), "Unable to parse platforms config")

        platform = TargetPlatform.NONE

        for platform_name in data:
            new_platform = TargetPlatform.get_default_values().get(platform_name, None)
            if new_platform is None:
                raise RuntimeError(f"Unknown platform {platform_name}")
            platform = platform.union(new_platform)

        return platform


class RootElement(ParserBlock):
    def __init__(self):
        super().__init__(None)
        self.artifacts: Dict[str, ArtifactElement] = {}
        self.platforms: TargetPlatform = TargetPlatform.NONE
        self.build_order: List[ArtifactElement] = []

    def get_block_type(self) -> str:
        return "root"

    def get_name(self):
        return "<ROOT>"

    @staticmethod
    @type_guard
    def parse_from_json(data: dict) -> 'RootElement':
        error_on_fail(check_dict_types(data,
            {"artifacts": dict,
             "config": Optional[dict],
             "platforms": Optional[List[str]]
             }), "Missing information or wrong types for parsing root block:")

        block = RootElement()

        block.config = deepcopy_dict_remove_private(data.get("config", {}))
        block.artifacts = {}
        block.platforms = ParserBlock.platform_from_json(data.get("platforms", []))

        for artifact_name, artifact_config in deepcopy_dict_remove_private(data.get('artifacts', {})).items():
            block.artifacts[artifact_name] = ArtifactElement.parse_from_json(artifact_config, artifact_name, block)

        return block


class ArtifactElement(ParserBlock):
    @type_guard
    def __init__(self, parent: RootElement):
        super().__init__(parent)
        self.groups: List[GroupElement] = []
        self.dependencies: List[ArtifactElement] = []
        self.artifact_name: str = None
        self.platforms: TargetPlatform = TargetPlatform.NONE

    def get_block_type(self) -> str:
        return "artifact"

    def get_name(self):
        return str(self.artifact_name)

    @staticmethod
    @type_guard
    def parse_from_json(data: dict, artifact_name: str, parent: RootElement) -> "ArtifactElement":
        error_on_fail(check_dict_types(data, {
                "stages": list,
                "config": Optional[dict],
                "dependencies": Optional[List[str]],
                "platforms": Optional[List[str]],
             }), f"Missing information or wrong types for parsing artifact {artifact_name}:")

        block = ArtifactElement(parent=parent)
        block.config = deepcopy_dict_remove_private(data.get("config", {}))
        block.groups = []
        block.artifact_name = artifact_name
        block.platforms = ParserBlock.platform_from_json(data.get("platforms", []))

        for i, group_config in enumerate(data.get("stages", [])):
            block.groups.append(GroupElement.parse_from_json(group_config, block, artifact_name, i))

        return block


class GroupElement(ParserBlock):
    @type_guard
    def __init__(self, parent: ArtifactElement):
        super().__init__(parent)
        self.group_name: str = ""
        self.group_index: int = -1
        self.raw_dependencies: List[str] = []
        self.dependencies: List[Tuple[ArtifactElement, Platform, Architecture]] = []
        self.template: Optional[GroupTemplate] = None

    def get_block_type(self) -> str:
        return "group"

    def get_name(self):
        return f"{self.parent.get_name()}:{self.group_index}:{self.group_name}"

    @staticmethod
    @type_guard
    def parse_from_json(data: dict, parent: ArtifactElement, artifact_name: str, group_index: int) -> "GroupElement":
        error_on_fail(check_dict_types(data, {
            "name": str,
            "config": Optional[dict],
            "dependencies": Optional[List[str]],
        }), f"Missing information or wrong types to parse group {data.get('name', 'unknown')} for artifact {artifact_name}:{group_index}:")

        block = GroupElement(parent=parent)
        block.group_name = data.get("name")
        block.group_index = group_index
        block.raw_dependencies = copy.deepcopy(data.get("dependencies", []))
        block.config = deepcopy_dict_remove_private(data.get("config", {}))

        return block


class ConfigParser:
    def __init__(self):
        self._root: RootElement = None
        self._targets: Optional[List[str]] = None
        self.__lock = threading.Lock()
        self._dependency_graph: nx.DiGraph = None
        self.build_order: List[str] = []

    def get_artifact(self, name: str) -> Optional[ArtifactElement]:
        for k, v in self._root.artifacts.items():
            if k == name:
                return v
        return None

    @type_guard
    def parse(self, config: dict, targets: Optional[List[str]] = None) -> RootElement:
        LOGGER.debug("Parsing config")
        with self.__lock:
            self._root = RootElement.parse_from_json(config)
            self._targets = targets

            self._resolve_platforms()
            self._resolve_dependencies()
            self._compute_dependency_order()
            self._match_templates()

            return self._root

    def get_build_plan(self) -> List[ArtifactElement]:
        result = []
        for target in self.build_order:
            block = self.get_artifact(target)
            if block is None:
                raise RuntimeError(f"Unable to find artifact {target}")
            result.append(block)
        return result

    def _resolve_platforms(self):
        if self._root.platforms.is_empty():
            LOGGER.info("No platforms specified for root, using ALL platform")
            self._root.platforms = TargetPlatform.ALL

        remove_artifacts = []

        for artifact_name, artifact in self._root.artifacts.items():
            platform = artifact.platforms

            if platform.is_empty():
                LOGGER.info(f"No platforms specified for artifact {artifact_name}, using ALL platform")
                artifact.platforms = TargetPlatform.ALL

            intersected_platform = artifact.platforms.intersection(self._root.platforms)

            if intersected_platform != artifact.platforms:
                LOGGER.debug(f"Artifact {artifact_name} has platforms that are not supported by root, removing them")

            if intersected_platform.is_empty():
                LOGGER.warning(f"Artifact {artifact_name} has no target platforms after intersection with root, removing it")
                remove_artifacts.append(artifact_name)

            artifact.platforms = intersected_platform

        for artifact_name in remove_artifacts:
            del self._root.artifacts[artifact_name]

    def _resolve_dependencies(self):
        LOGGER.debug("Resolving dependencies")

        self._dependency_graph = nx.DiGraph()

        for artifact_name in self._root.artifacts.keys():
            self._dependency_graph.add_node(artifact_name)

        for artifact_name, artifact_block in self._root.artifacts.items():
            collected_dependencies: List[str] = []

            for group_block in artifact_block.groups:
                for task_dependency in group_block.raw_dependencies:
                    check_type(task_dependency, str)
                    assert isinstance(task_dependency, str)
                    if ":" in task_dependency:
                        collected_dependencies.append(task_dependency[:task_dependency.index(":")])
                    else:
                        collected_dependencies.append(task_dependency)

            linked_dependecies = []
            for dependency in sorted(set(collected_dependencies)):
                if dependency not in self._root.artifacts:
                    raise RuntimeError(f"Artifact {artifact_name} depends on artifact {dependency} which is not defined")

                dependency_block = self.get_artifact(dependency)
                linked_dependecies.append(dependency_block)

                self._dependency_graph.add_edge(artifact_name, dependency)

            artifact_block.dependencies = linked_dependecies

            for group_block in artifact_block.groups:
                task_dependencies = []
                for i, task_dependency in enumerate(group_block.raw_dependencies):
                    check_type(task_dependency, str)

                    working = task_dependency
                    dep_name = task_dependency
                    dep_platform = Platform.DUMMY
                    dep_architecture = Architecture.DUMMY

                    if ":" in working:
                        dep_name = working[:working.index(":")]
                        working = working[working.index(":") + 1:]

                        if ":" in working:
                            dep_platform = Platform.get_platform_from_name(working[:working.index(":")])
                            if dep_platform == Platform.UNKNOWN:
                                raise RuntimeError(f"Unknown platform {working[:working.index(':')]} in dependency {task_dependency}")

                            working = working[working.index(":") + 1:]
                            dep_architecture = Architecture.get_architecture_from_name(working)

                            if dep_architecture == Architecture.UNKNOWN:
                                raise RuntimeError(f"Unknown architecture {working} in dependency {task_dependency}")
                        else:
                            dep_platform = Platform.get_platform_from_name(working)
                            if dep_platform == Platform.UNKNOWN:
                                raise RuntimeError(f"Unknown platform {working} in dependency {task_dependency}")

                    dependency_block = self.get_artifact(dep_name)
                    assert isinstance(dependency_block, ArtifactElement)
                    task_dependencies.append((dependency_block, dep_platform, dep_architecture))
                group_block.dependencies = task_dependencies

        LOGGER.debug("Checking for dependency cycles")
        dependency_cycles = list(nx.simple_cycles(self._dependency_graph))
        if len(dependency_cycles) > 0:
            raise RuntimeError(f"Found cyclic dependencies between artifacts {','.join(dependency_cycles[0])}")

    def _compute_dependency_order(self):
        sub_nodes = []

        if self._targets is None:
            LOGGER.debug("No targets specified, building all artifacts")
            sub_nodes = self._dependency_graph.nodes()
        else:
            for target in self._targets:
                if target not in self._dependency_graph.nodes():
                    raise RuntimeError(f"Target {target} is not defined")
                sub_nodes.append(target)
                sub_nodes.append(*nx.descendants(self._dependency_graph, target))

        target_nodes = sorted(set(sub_nodes))
        for node in list(self._dependency_graph.nodes()):
            if node not in target_nodes:
                self._dependency_graph.remove_node(node)
                LOGGER.debug(f"Not building artifact {node} as it is not in the target list or a dependency")

        # Possible because we have checked for cycles
        topological_sort = list(nx.topological_sort(self._dependency_graph))
        topological_sort.reverse()
        self.build_order = topological_sort

        self._root.build_order = [self.get_artifact(x) for x in self.build_order]

        LOGGER.debug(f"Building artifacts {', '.join(self.build_order)}")

    def _match_templates(self):
        for artifact_name, artifact_block in self._root.artifacts.items():
            for group_block in artifact_block.groups:
                # Prefer group groups before individual groups
                group = GroupDatabase.get_instance().get_group(group_block.group_name)

                if group is None:
                    LOGGER.error(f"Unable to find group {group_block}")
                    raise RuntimeError(f"Unable to find group {group_block}")

                group_block.template = group
