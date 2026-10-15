"""
pltdata — Mock Platform Framework
==================================
Stub implementation of the data platform framework API.
Mirrors the real pltdata package interface for demo and local development use.

Real framework classes are replaced with stubs that log intent rather than
executing actual Databricks/Delta operations.

Usage
-----
    from pltdata import Layer, AttrType, EntityType, FieldType
    from pltdata import Parameter, EntityProperty, RetentionDuration
    from pltdata import Attribute, Entity, Drl
    from pltdata import PltDebugTransform, PltDataFrame, LifecycleHandler
    from pltdata import StagingIngestionLifecycleHandler, EnrichedIngestionLifecycleHandler
    from pltdata import Deploy, LakeConnectFactory, SchemaTranslate
"""

from ._types import Layer, AttrType, EntityType, FieldType
from ._models import Parameter, EntityProperty, RetentionDuration, Attribute, Entity
from ._drl import Drl
from ._transform import (
    PltDebugTransform,
    PltDataFrame,
    LifecycleHandler,
    StagingIngestionLifecycleHandler,
    EnrichedIngestionLifecycleHandler,
)
from ._deploy import Deploy
from ._lake_connect import LakeConnectFactory
from ._schema import SchemaTranslate

__all__ = [
    # Enums
    "Layer",
    "AttrType",
    "EntityType",
    "FieldType",
    # Data models
    "Parameter",
    "EntityProperty",
    "RetentionDuration",
    "Attribute",
    "Entity",
    # Registry
    "Drl",
    # Transform
    "PltDebugTransform",
    "PltDataFrame",
    "LifecycleHandler",
    "StagingIngestionLifecycleHandler",
    "EnrichedIngestionLifecycleHandler",
    # Infrastructure
    "Deploy",
    "LakeConnectFactory",
    "SchemaTranslate",
]
