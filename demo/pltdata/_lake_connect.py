"""LakeConnectFactory stub — provides a mock lake_connection for local/demo use."""
from __future__ import annotations
import os
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ._types import Layer


class _LakeConnection:
    """
    Mock lake connection — returns configurable environment values.
    Set PLATFORM_ENVIRONMENT env var to switch between 'dev', 'qua', 'prd'.
    """

    def __init__(self):
        self._env = os.environ.get("PLATFORM_ENVIRONMENT", "dev")

    @property
    def product_environment(self) -> str:
        return self._env

    @property
    def business_unit(self) -> str:
        return os.environ.get("PLATFORM_BUSINESS_UNIT", "demo")

    @property
    def platform_product(self) -> str:
        return os.environ.get("PLATFORM_PRODUCT", "int")

    def get_root(self, layer: "Layer") -> str:
        return f"/mnt/platform/{self._env}/{layer.value}"

    def sql(self, query: str):
        print(f"[LakeConnection] sql() — would execute:\n{query.strip()}")
        return None


class LakeConnectFactory:
    _connection: Optional[_LakeConnection] = None

    @property
    def lake_connection(self) -> _LakeConnection:
        if LakeConnectFactory._connection is None:
            LakeConnectFactory._connection = _LakeConnection()
        return LakeConnectFactory._connection
