"""Deploy stub — registers entities in the platform framework registry."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._models import Entity


class Deploy:
    """Registers an Entity in the platform data registry."""

    def deploy_entity(self, entity: "Entity") -> None:
        print(
            f"[Deploy] Registering entity: {entity.entity_name!r} "
            f"| layer={entity.layer.value} "
            f"| locator={entity.entity_locator!r} "
            f"| attributes={len(entity.attributes)}"
        )
