"""Core enums — mirrors the real pltdata type system."""
from enum import Enum


class Layer(Enum):
    RAW = "raw"
    STAGING = "staging"
    ENRICHED = "enriched"
    CURATED = "curated"
    SERVING = "serving"


class AttrType(Enum):
    STRING = "string"
    INT = "integer"
    LONG = "long"
    FLOAT = "float"
    DOUBLE = "double"
    BOOLEAN = "boolean"
    TIMESTAMP = "timestamp"
    DATE = "date"
    STRUCT = "struct"
    ARRAY = "array"
    EXTERNALID = "externalid"


class EntityType(Enum):
    DELTA = "delta"
    DELTA_MANAGED = "delta_managed"


class FieldType(Enum):
    P_KEY = "partition_key"
