"""SchemaTranslate stub — converts Entity attribute definitions to Spark schemas."""
from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Any

if TYPE_CHECKING:
    from ._models import Entity
    from ._types import AttrType

_ATTR_TYPE_MAP = {
    "string": "StringType()",
    "integer": "IntegerType()",
    "long": "LongType()",
    "float": "FloatType()",
    "double": "DoubleType()",
    "boolean": "BooleanType()",
    "timestamp": "TimestampType()",
    "date": "DateType()",
}


class SchemaTranslate:
    """Translates Entity attribute definitions into Spark StructType schemas."""

    def __init__(self, entity: "Entity"):
        self._entity = entity

    def get_schema(self) -> Any:
        """Return a Spark StructType matching the entity's attribute list."""
        try:
            from pyspark.sql.types import StructType, StructField, StringType
            fields = [
                StructField(a.name, StringType(), True)
                for a in self._entity.attributes
            ]
            return StructType(fields)
        except ImportError:
            print(f"[SchemaTranslate] Spark not available — returning None for {self._entity.entity_name!r}")
            return None

    def get_empty_dataframe(self) -> Optional[Any]:
        """Return an empty Spark DataFrame matching the entity schema."""
        try:
            from pyspark.sql import SparkSession
            spark = SparkSession.getActiveSession()
            if spark:
                schema = self.get_schema()
                return spark.createDataFrame([], schema)
        except Exception as e:
            print(f"[SchemaTranslate] get_empty_dataframe() failed: {e}")
        return None
