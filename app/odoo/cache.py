"""Process-local, unbounded dict cache for Odoo lookups. Lives only as long as
its owning ``OdooContext`` (one drain cycle), so staleness is bounded.

Ported from ``pymigrate/migrate-worker/app/odoo/odoo_cache.py``.
"""

from typing import Any, Callable, Optional


class OdooCache:
    def __init__(self):
        self._internal: dict[Any, Any] = {}

    def get(self, name) -> Any | None:
        return self._internal.get(name)

    def get_or_throw(self, name, error_fn: Optional[Callable[[], Exception]] = None) -> Any:
        value = self.get(name)
        if value is None:
            raise (
                error_fn()
                if error_fn
                else KeyError(f'No se encontró un valor para {name} en el cache.')
            )
        return value

    def set(self, name, value) -> None:
        self._internal[name] = value
