import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from expkit.base.architecture import TargetPlatform, Platform, Architecture
from expkit.base.logger import get_logger

from expkit.base.payload import Payload, PayloadType
from expkit.base.stage.base import StageTemplate
from expkit.base.utils.type_checking import type_guard


LOGGER = get_logger(__name__)


class StageTemplateGroupCacheEntry:
    def __init__(self, platform: Platform, architecture: Architecture, input_type: PayloadType, dependencies: List[PayloadType], output_type: PayloadType, stages: List[StageTemplate]):
        self.platform = platform
        self.architecture = architecture
        self.input_type = input_type
        self.output_type = output_type
        self.dependencies = dependencies
        self.stages = stages


class StageTemplateGroup:
    """Representation of a platform-independent stage template group."""

    @type_guard
    def __init__(self, name: str, description: str, stages: Optional[List[StageTemplate]]=None):
        self.name = name
        self.description = description
        self.stages = stages if stages is not None else []

        self.__cache_valid = False
        self.__cache_lock = threading.RLock()
        self.__cache: List[StageTemplateGroupCacheEntry] = []
        self.__cache_platforms_archs: List[Tuple[Platform, Architecture]] = []
        self.__cache_input_types: Dict[Tuple[Platform, Architecture], List[Tuple[List[PayloadType], List[PayloadType]]]] = {} # values are dependency types and output types
        self.__cache_output_types: Dict[Tuple[Platform, Architecture, PayloadType, List[PayloadType]], List[PayloadType]] = {}

    def _invalidate_cache(self):
        with self.__cache_lock:
            self.__cache_valid = False

    @property
    def _cache(self):
        with self.__cache_lock:
            if not self.__cache_valid:
                self.__build_cache()

            return self.__cache

    @property
    def _cache_platforms_arch(self) -> List[Tuple[Platform, Architecture]]:
        with self.__cache_lock:
            if not self.__cache_valid:
                self.__build_cache()

            return self.__cache_platforms_archs

    @property
    def _cache_input_types(self) -> Dict[Tuple[Platform, Architecture], List[Tuple[List[PayloadType], List[PayloadType]]]]:
        with self.__cache_lock:
            if not self.__cache_valid:
                self.__build_cache()

            return self.__cache_input_types

    @property
    def _cache_output_types(self) -> Dict[Tuple[Platform, Architecture, PayloadType, List[PayloadType]], List[PayloadType]]:
        with self.__cache_lock:
            if not self.__cache_valid:
                self.__build_cache()

            return self.__cache_output_types

    def add_stage(self, stage: StageTemplate):
        with self.__cache_lock:
            if stage in self.stages:
                return

            self._invalidate_cache()
            self.stages.append(stage)

    def _get_cache_entry(self, platform: Platform, architecture: Architecture, input_type: PayloadType, dependencies: List[PayloadType], output_type: PayloadType) -> Optional[List[StageTemplate]]:
        assert platform.is_single()
        assert architecture.is_single()

        for entry in self._cache:
            if entry.platform == platform and entry.architecture == architecture and entry.input_type == input_type and entry.output_type == output_type:
                ok = True
                for etype, dtype in zip(entry.dependencies, dependencies):
                    if etype != dtype:
                        ok = False
                        break
                if ok:
                    return entry.stages
        return None

    def __build_cache(self):
        with self.__cache_lock:
            self.__cache = []
            self.__cache_valid = True
            self.__cache_platforms_archs = []
            self.__cache_input_types = {}
            self.__cache_dependency_types = {}
            self.__cache_output_types = {}

            for stage in self.stages:
                for platform, arch in stage.platform:
                    system = (platform, arch)

                    self.__cache_platforms_archs.append(system)
                    input_types = stage.get_supported_input_payload_types()

                    if not system in self.__cache_input_types:
                        self.__cache_input_types[system] = []

                    self.__cache_input_types[system].extend(input_types)
                    self.__cache_input_types[system] = list(set(self.__cache_input_types[system]))

                    for input_type in input_types:
                        for dependency_set in stage.get_supported_dependency_types():
                            system = (platform, arch, input_type)

                            output_types = stage.get_output_payload_type(input_type, dependency_set)

                            if not system in self.__cache_output_types:
                                self.__cache_output_types[system] = []

                            input_combi = (dependency_set, output_types)
                            if input_combi not in self.__cache_output_types[system]:
                                self.__cache_output_types[system].append(input_combi)

                            for output_type in stage.get_output_payload_type(input_type, dependency_set):
                                cache_entries = self._get_cache_entry(platform, arch, input_type, dependency_set, output_type)

                                if cache_entries is None:
                                    cache_entries = []
                                    self.__cache.append(StageTemplateGroupCacheEntry(platform, arch, input_type, dependency_set, output_type, cache_entries))

                                cache_entries.append(stage)

            self.__cache_platforms_archs = list(set(self.__cache_platforms_archs))

    def get_supported_platforms(self) -> List[Tuple[Platform, Architecture]]:
        return self._cache_platforms_arch

    def get_supported_input_payload_types(self, platform: Platform, architecture: Architecture) -> List[PayloadType]:
        assert platform.is_single()
        assert architecture.is_single()

        return self._cache_input_types.get((platform, architecture), [])

    def get_output_payload_type(self, platform: Platform, architecture: Architecture, input_type: PayloadType, dependencies: List[PayloadType]) -> List[PayloadType]:
        assert platform.is_single()
        assert architecture.is_single()

        return self.__cache_output_types.get((platform, architecture, input_type, dependencies), [])

    def get_stage(self, platform: Platform, architecture: Architecture, input_type: PayloadType, dependencies: List[PayloadType], output_type: PayloadType) -> Optional[StageTemplate]:
        assert platform.is_single()
        assert architecture.is_single()

        stages = self._get_cache_entry(platform, architecture, input_type, dependencies, output_type)

        if len(stages) <= 0:
            return None
        elif len(stages) == 1:
            return stages[0]
        else:
            # Todo: Later perhaps allow function overwrite to chose desired stage
            LOGGER.error(f"Multiple stages found for group {self.name} query")
            LOGGER.error(f" - Platform: {platform}")
            LOGGER.error(f" - Architecture: {architecture}")
            LOGGER.error(f" - Input Type: {input_type}")
            LOGGER.error(f" - Dependencies: {dependencies}")
            LOGGER.error(f" - Output Type: {output_type}")
            LOGGER.error(f" - Stages found:")
            for stage in stages:
                LOGGER.error(f"   - {stage.name}")
            raise Exception("Multiple stages support the same platform-architecture-input-output combination.")

    @type_guard
    def execute(self, payload: Payload, output_type: PayloadType, platform: Platform, architecture: Architecture, parameters: dict, build_directory: Path) -> Payload:
        LOGGER.info(f"Executing stage group {self.name} ({payload.type} -> {output_type}) on {platform} {architecture}")

        assert platform.is_single()
        assert architecture.is_single()

        stage = self.get_stage(platform, architecture, payload.type, output_type)

        if stage is None:
            raise Exception("No stage found for platform-architecture-input-output combination.")

        payload = stage.execute(payload, output_type, platform, architecture, parameters, build_directory)

        if payload.type != output_type:
            raise Exception("Stage did not produce the expected output type.")

        LOGGER.debug(f"Executed stage group {self.name} ({payload.type} -> {output_type}) on {platform} {architecture}")

        return payload

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name