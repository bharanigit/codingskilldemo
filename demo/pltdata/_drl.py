"""Data Registry Locator — stub mirrors the real Drl API."""
from __future__ import annotations
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ._models import Entity
    from ._types import Layer


class _DrlResult:
    """Returned by Drl.from_object / Drl.from_config — provides schema info stubs."""

    def __init__(self, locator: str, enforce_schema: bool = True):
        self._locator = locator
        self._enforce_schema = enforce_schema

    def get_all_but_technical_columns_for_hashing(self):
        print(f"[DRL] get_all_but_technical_columns_for_hashing() for {self._locator}")
        return []

    def __repr__(self) -> str:
        return f"Drl({self._locator!r})"


class Drl:
    @classmethod
    def from_object(cls, entity: "Entity", enforce_schema: bool = True) -> _DrlResult:
        """Build a DRL from an Entity instance (used in PltDebugTransform target)."""
        return _DrlResult(entity.entity_locator, enforce_schema)

    @classmethod
    def from_config(
        cls,
        entity_name: str,
        product: str,
        module: str,
        layer: "Layer",
    ) -> _DrlResult:
        """Build a DRL from registry config (used in Drl.from_config lookups)."""
        locator = f"{layer.value}/{product}/{module}/{entity_name}"
        return _DrlResult(locator)
