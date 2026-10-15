"""Data model classes — mirrors pltdata Parameter, Attribute, Entity, etc."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Any

from ._types import Layer, AttrType, EntityType, FieldType


@dataclass
class Parameter:
    name: str
    value: str


@dataclass
class EntityProperty:
    auto_compute_hash: bool = False
    auto_compute_loadinfo: bool = False


@dataclass
class RetentionDuration:
    dev: Optional[int] = None
    qua: Optional[int] = None
    prd: Optional[int] = None


@dataclass
class Attribute:
    name: str
    display_name: str = ""
    description: str = ""
    is_key: bool = False
    is_array: bool = False
    attr_type: Optional[AttrType] = None
    field_type: Optional[FieldType] = None
    attr_len: Optional[int] = None
    source: Optional[List[str]] = None
    struct: Optional[List["Attribute"]] = None
    parameter: Optional[List[Parameter]] = None

    def __repr__(self) -> str:
        return f"Attribute(name={self.name!r}, attr_type={self.attr_type})"


class Entity:
    def __init__(
        self,
        entity_name: str,
        entity_type: EntityType,
        module_name: str,
        entity_locator: str,
        source: List[Any],
        layer: Layer,
        product: str,
        version: str,
        source_system: str,
        is_public: bool = False,
        parameter: Optional[List[Parameter]] = None,
        entity_property: Optional[EntityProperty] = None,
        attributes: Optional[List[Attribute]] = None,
        retention_duration: Optional[RetentionDuration] = None,
        increment_driver_source_entity_name: Optional[str] = None,
    ):
        self.entity_name = entity_name
        self.entity_type = entity_type
        self.module_name = module_name
        self.entity_locator = entity_locator
        self.source = source or []
        self.layer = layer
        self.product = product
        self.version = version
        self.source_system = source_system
        self.is_public = is_public
        self.parameter = parameter or []
        self.entity_property = entity_property or EntityProperty()
        self.attributes = attributes or []
        self.retention_duration = retention_duration
        self.increment_driver_source_entity_name = increment_driver_source_entity_name

    def __repr__(self) -> str:
        return (
            f"Entity(name={self.entity_name!r}, layer={self.layer}, "
            f"locator={self.entity_locator!r})"
        )
