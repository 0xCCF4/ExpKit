import copy
import threading
from typing import Optional, List, Union
import networkx as nx

from expkit.base.architecture import PlatformArchitecture, Platform, Architecture, PLATFORM_ARCHITECTURES
from expkit.base.logger import get_logger
from expkit.base.utils import check_dict_types, error_on_fail, deepcopy_dict_remove_private, check_type
from expkit.framework.database import StageGroupDatabase, StageDatabase

LOGGER = get_logger(__name__)


class ParserBlock:
    def __init__(self, name: str, data: dict, parent: 'ParserBlock' = None):
        self.name = name
        self.parent = parent
        self.data = data
        self.template = None
        self._config_cache = None

    def __str__(self):
        return f"{self.name}({self.get_name()})"

    def __repr__(self):
        return str(self)

    def get_name(self):
        if self.name == "root":
            return "<ROOT>"
        elif self.name == "artifact":
            return self.data["id"]
        elif self.name == "stage":
            return self.data["name"]

    def get_config(self) -> dict:
        if not self._config_cache:
            self._config_cache = {}

            if self.name == "root":
                self._config_cache = copy.deepcopy(self.data["config"])
            elif self.name == "artifact" or self.name == "stage":
                self._config_cache = copy.deepcopy(self.parent.get_config()) # use parent config as template
                for key, value in self.data["confi"].items(): # override with current config
                    self._config_cache[key] = copy.deepcopy(value)
            else:
                raise RuntimeError(f"Unknown block type: {self.name}")

        return self._config_cache


class ConfigParser:
    def __init__(self):
        self._root: ParserBlock = None
        self._targets: Optional[List[str]] = None
        self.__lock = threading.Lock()
        self._dependency_graph: nx.DiGraph = None
        self.build_order: List[str] = []

    def get_artifact(self, name: str) -> Optional[ParserBlock]:
        assert self._root is not None and self._root.name == "root"

        for k, v in self._root.data["artifacts"].items():
            if k == name:
                return v
        return None

    def parse(self, config: dict, targets: Optional[List[str]] = None) -> ParserBlock:
        LOGGER.debug("Parsing config")
        with self.__lock:
            self._root = self._parse_root(config)
            self._targets = targets

            self._resolve_platforms()
            self._resolve_dependencies()
            self._compute_dependency_order()
            #self._match_templates()

            return self._root

    def get_build_plan(self) -> List[ParserBlock]:
        result = []
        for target in self.build_order:
            block = self.get_artifact(target)
            if block is None:
                raise RuntimeError(f"Unable to find artifact {target}")
            result.append(block)
        return result

    def _parse_root(self, config: dict) -> ParserBlock:
        error_on_fail(check_dict_types(
            {"artifacts": dict,
             "config": Optional[dict],
             "platforms": Optional[List[str]]
             }, config), "Unable to parse root config")

        block = ParserBlock("root", {
            "config": deepcopy_dict_remove_private(config.get("config", {})),
            "artifacts": {},
            "platforms": self._parse_platforms(config.get("platforms", []))
        })

        for artifact_name, artifact_config in deepcopy_dict_remove_private(config.get('artifacts', {})).items():
            block.data["artifacts"][artifact_name] = self._parse_artifact(artifact_config, block, artifact_name)

        return block

    def _parse_platforms(self, config: list) -> PlatformArchitecture:
        error_on_fail(check_type(List[str], config), "Unable to parse platforms config")

        platform = PLATFORM_ARCHITECTURES["NONE"]

        for platform_name in config:
            new_platform = PLATFORM_ARCHITECTURES.get(platform_name, None)
            if new_platform is None:
                raise RuntimeError(f"Unknown platform {platform_name}")
            platform = platform.merge(new_platform)

        return platform

    def _parse_artifact(self, config: dict, root: ParserBlock, artifact_name: str) -> ParserBlock:
        error_on_fail(check_dict_types(
            {"stages": list,
             "config": Optional[dict],
             "dependencies": Optional[list],
             "platforms": Optional[List[str]],
             }, config), f"Unable to parse artifact {artifact_name} config")

        block = ParserBlock("artifact", {
            "config": deepcopy_dict_remove_private(config.get("config", {})),
            "dependencies": copy.deepcopy(config.get("dependencies", [])),
            "stages": [],
            "id": artifact_name,
            "platforms": self._parse_platforms(config.get("platforms", []))
        }, root)

        for dependency in block.data["dependencies"]:
            error_on_fail(check_type(str, dependency), f"Unable to parse artifact {artifact_name} dependency")

        for stage_config in config.get("stages", []):
            block.data["stages"].append(self._parse_stage(stage_config, block, artifact_name))

        return block

    def _parse_stage(self, config: dict, parent: ParserBlock, artifact_name: str) -> ParserBlock:
        error_on_fail(check_dict_types({
            "name": str,
            "config": Optional[Union[str, dict]],
            "dependencies": Optional[List[str]],
        }, config), f"Unable to parse stage {config.get('name', 'unknown')} for artifact {artifact_name}")

        internal_config = config.get("config", None)

        block = ParserBlock("stage", {
            "name": config["name"],
            "config": None,
            "dependencies": copy.deepcopy(config.get("dependencies", [])),
        }, parent)

        if internal_config is None:
            block.data["config"] = {}
        elif isinstance(internal_config, dict):
            block.data["config"] = deepcopy_dict_remove_private(internal_config)
        elif isinstance(internal_config, str):
            block.data["config"] = {"default": internal_config}
        else:
            raise RuntimeError("Wrong typing information after type checking")

        return block

    def _resolve_platforms(self):
        assert self._root is not None and self._root.name == "root"

        if self._root.data["platforms"].is_empty():
            LOGGER.info("No platforms specified for root, using ALL platform")
            self._root.data["platforms"] = PLATFORM_ARCHITECTURES["ALL"]

        remove_artifacts = []

        for artifact_name, artifact in self._root.data["artifacts"].items():
            platform = artifact.data["platforms"]

            if platform.is_empty():
                LOGGER.info(f"No platforms specified for artifact {artifact_name}, using ALL platform")
                artifact.data["platforms"] = PLATFORM_ARCHITECTURES["ALL"]

            intersected_platform = artifact.data["platforms"].intersection(self._root.data["platforms"])

            if intersected_platform != artifact.data["platforms"]:
                LOGGER.debug(f"Artifact {artifact_name} has platforms that are not supported by root, removing them")

            if intersected_platform.is_empty():
                LOGGER.warning(f"Artifact {artifact_name} has no target platforms after intersection with root, removing it")
                remove_artifacts.append(artifact_name)

            artifact.data["platforms"] = intersected_platform

        for artifact_name in remove_artifacts:
            del self._root.data["artifacts"][artifact_name]

    def _resolve_dependencies(self):
        LOGGER.debug("Resolving dependencies")
        assert self._root is not None and self._root.name == "root"

        self._dependency_graph = nx.DiGraph()

        for artifact_name in self._root.data["artifacts"].keys():
            self._dependency_graph.add_node(artifact_name)

        for artifact_name, artifact_block in self._root.data["artifacts"].items():
            assert artifact_block.name == "artifact"

            collected_dependencies = []

            for manual_dependency in artifact_block.data["dependencies"]:
                collected_dependencies.append(manual_dependency)

            for stage_block in artifact_block.data["stages"]:
                assert stage_block.name == "stage"
                for task_dependency in stage_block.data.get("dependencies", []):
                    collected_dependencies.append(task_dependency)

            linked_dependecies = []
            for dependency in sorted(set(collected_dependencies)):
                if dependency not in self._root.data["artifacts"]:
                    raise RuntimeError(f"Artifact {artifact_name} depends on artifact {dependency} which is not defined")

                dependency_block = self._root.data["artifacts"][dependency]
                linked_dependecies.append(dependency_block)

                self._dependency_graph.add_edge(artifact_name, dependency)

            artifact_block.data["dependencies"] = linked_dependecies

            for stage_block in artifact_block.data["stages"]:
                assert stage_block.name == "stage"
                task_dependencies = []
                for task_dependency in stage_block.data.get("dependencies", []):
                    dependency_block = self._root.data["artifacts"][task_dependency]
                    task_dependencies.append(dependency_block)
                stage_block.data["dependencies"] = task_dependencies

        LOGGER.debug("Checking for dependency cycles")
        dependency_cycles = list(nx.simple_cycles(self._dependency_graph))
        if len(dependency_cycles) > 0:
            raise RuntimeError(f"Found cyclic dependencies between artifacts {','.join(dependency_cycles[0])}")

    def _compute_dependency_order(self):
        assert self._root is not None and self._root.name == "root"

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

        LOGGER.debug(f"Building artifacts {', '.join(self.build_order)}")

    def _match_templates(self):
        assert self._root is not None and self._root.name == "root"

        for artifact_name, artifact_block in self._root.data["artifacts"].items():
            assert artifact_block.name == "artifact"

            for stage_block in artifact_block.data["stages"]:
                assert stage_block.name == "stage"

                # Prefer stage groups before individual stages
                group = StageGroupDatabase.get_instance().get_group(stage_block.data["name"])

                if group is None:
                    LOGGER.error(f"Unable to find stage group {stage_block.data['name']}")
                    raise RuntimeError(f"Unable to find stage group {stage_block.data['name']}")

                stage_block.template = group
