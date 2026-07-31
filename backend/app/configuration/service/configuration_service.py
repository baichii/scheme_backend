from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from backend.app.configuration.schema.configuration import (
    ConfigurationCatalog,
    EnvironmentTemplateDocument,
    GetEnvironmentTemplate,
    GetScenarioType,
    GetScenarioTypeSide,
    ScenarioTypeDocument,
)
from backend.core.path_conf import BASE_PATH

CONFIGURATION_PATH = BASE_PATH.parent / "config"


class UniqueKeyLoader(yaml.SafeLoader):
    def construct_mapping(self, node: yaml.MappingNode, deep: bool = False) -> dict:
        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in mapping:
                raise ValueError(f"duplicate YAML key: {key}")
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


def _read_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return yaml.load(stream, Loader=UniqueKeyLoader)


class ConfigurationService:
    """加载并验证 Backend 内置产品配置。"""

    def __init__(self, path: Path = CONFIGURATION_PATH) -> None:
        self.path = path
        self.catalog: ConfigurationCatalog
        self.environment_documents: dict[str, EnvironmentTemplateDocument]
        self.scenario_documents: dict[str, ScenarioTypeDocument]
        self._load()

    def _load(self) -> None:
        self.catalog = ConfigurationCatalog.model_validate(_read_yaml(self.path / "index.yaml"))
        self.environment_documents = self._load_documents(
            self.path / "environment_templates", EnvironmentTemplateDocument
        )
        self.scenario_documents = self._load_documents(
            self.path / "scenario_types", ScenarioTypeDocument, exclude={"schema.example.yaml"}
        )
        self._validate_references()

    @staticmethod
    def _load_documents(
        path: Path,
        model: type[EnvironmentTemplateDocument] | type[ScenarioTypeDocument],
        *,
        exclude: set[str] | None = None,
    ) -> dict[str, Any]:
        documents: dict[str, Any] = {}
        for file_path in sorted(path.glob("*.yaml")):
            if file_path.name in (exclude or set()):
                continue
            document = model.model_validate(_read_yaml(file_path))
            if document.key in documents:
                raise ValueError(f"duplicate configuration key: {document.key}")
            documents[document.key] = document
        return documents

    def _validate_references(self) -> None:
        if set(self.catalog.environment_templates) != set(self.environment_documents):
            raise ValueError("environment template catalog does not match available documents")
        if set(self.catalog.scenario_types) != set(self.scenario_documents):
            raise ValueError("scenario type catalog does not match available documents")
        known_templates = set(self.environment_documents)
        scenario_owners: dict[str, str] = {}
        for document in self.scenario_documents.values():
            unknown = set(document.environment_templates) - known_templates
            if unknown:
                raise ValueError(f"scenario type {document.key} uses unknown templates: {sorted(unknown)}")
            for scenario in document.scenarios:
                if owner := scenario_owners.get(scenario):
                    raise ValueError(f"scenario {scenario} belongs to both {owner} and {document.key}")
                scenario_owners[scenario] = document.key

    def get_environment_templates(self) -> list[GetEnvironmentTemplate]:
        return [
            GetEnvironmentTemplate(
                key=document.key,
                name=document.name,
                description=document.description,
                fields=document.fields,
            )
            for key in self.catalog.environment_templates
            if (document := self.environment_documents.get(key))
        ]

    def get_scenario_types(self) -> list[GetScenarioType]:
        return [
            GetScenarioType(
                key=document.key,
                name=document.name,
                description=document.description,
                environment_template_keys=document.environment_templates,
                scenarios=document.scenarios,
                default_side_key=document.sides[0].key,
                sides=[
                    GetScenarioTypeSide(
                        key=side.key,
                        name=side.name,
                    )
                    for side in document.sides
                ],
            )
            for document in self.scenario_documents.values()
        ]


@lru_cache
def get_configuration_service() -> ConfigurationService:
    return ConfigurationService()


configuration_service = get_configuration_service()
