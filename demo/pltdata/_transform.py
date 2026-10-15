"""Transform runtime stubs — PltDebugTransform and PltDataFrame."""
from __future__ import annotations
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ._drl import _DrlResult


class PltDataFrame:
    """Thin wrapper around a Spark DataFrame — stub implementation."""

    def __init__(self, df: Any):
        self._df = df

    def display(self):
        if self._df is not None:
            self._df.show(10, truncate=False)

    @property
    def count(self) -> int:
        return self._df.count() if self._df is not None else 0

    @staticmethod
    def hash_columns_case_sensitive(cols):
        from pyspark.sql import functions as F
        col_exprs = [F.col(c[0]) for c in cols]
        return F.md5(F.concat_ws("|", *col_exprs))

    def __getattr__(self, name: str):
        return getattr(self._df, name)


class PltDebugTransform:
    """
    Platform transform wrapper — stub implementation for local/demo use.

    In a real Databricks environment this manages entity lifecycle,
    DRL registration, schema enforcement, and incremental processing.
    Here it logs intent and provides passthrough behaviour.
    """

    def __init__(
        self,
        notebook_variables: dict,
        version: str,
        target: Optional["_DrlResult"] = None,
        increment_driver_source_entity_name: Optional[str] = None,
        **kwargs,
    ):
        self._vars = notebook_variables
        self._version = version
        self._target = target
        self._increment_driver = increment_driver_source_entity_name
        print(
            f"[PltDebugTransform] Initialised — version={version!r}, "
            f"target={target!r}, increment_driver={increment_driver_source_entity_name!r}"
        )

    def end_transform(self, result: Any) -> None:
        """Signal end of transform — in prod writes result to the target entity table."""
        if result is None:
            print("[PltDebugTransform] end_transform(None) — no output (schema-only or schema-registration entity)")
        else:
            print(f"[PltDebugTransform] end_transform() — would persist result to {self._target!r}")

    def debug_cell(self) -> None:
        """Display debug info — in prod shows DRL metadata and execution context."""
        print(f"[PltDebugTransform] debug_cell() — target={self._target!r}")


class LifecycleHandler:
    """
    Override hook points in the platform transform flow.
    All methods default to pass — override only what you need.
    """

    def before_read(self) -> None:
        pass

    def after_read(self, df: Any) -> Any:
        return df

    def before_write(self, df: Any) -> Any:
        return df

    def after_write(self) -> None:
        pass


class StagingIngestionLifecycleHandler(LifecycleHandler):
    """Staging-layer lifecycle handler stub.

    Accepts either string locator paths or Drl objects — both call patterns
    are used across the skill reference files.
    """

    def __init__(self, source=None, target=None, **kwargs):
        print(
            f"[StagingIngestionLifecycleHandler] source={source!r}, target={target!r}"
        )


class EnrichedIngestionLifecycleHandler(LifecycleHandler):
    """Enriched-layer lifecycle handler stub.

    Accepts either string locator paths or Drl objects — both call patterns
    are used across the skill reference files.
    """

    def __init__(self, sources=None, target=None, **kwargs):
        print(
            f"[EnrichedIngestionLifecycleHandler] sources={sources!r}, target={target!r}"
        )
