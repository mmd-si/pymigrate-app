"""Per-model Odoo XML-RPC wrappers, consolidated from
``pymigrate/migrate-worker/app/odoo/*``.

Classes are ordered so every dependency is already in scope: the ``OdooModel``
base comes first, then the leaf lookup wrappers, and finally ``StockPicking``,
whose ``build_for_product`` signature references ``StockWarehouse`` and
``StockPickingType``.

Each wrapper carries its own ``OdooCache``; build a fresh set per drain cycle
(via ``OdooContext``) so cached master-data ids never go stale across cycles.
"""

import logging
from datetime import datetime, timezone

from app.odoo.cache import OdooCache
from app.odoo.connection import OdooConnection
from app.schemas.odoo import (
    M2MOp,
    OdooPickingState,
    OdooPriority,
    ProductTemplateSchema,
    StockMoveSchema,
    StockPickingSchema,
)

logger = logging.getLogger(__name__)

_SEP = ' / '


class OdooModel:
    model_name: str

    def __init__(self, conn: OdooConnection):
        self._conn = conn
        self._cache = OdooCache()

    async def _exec(self, method: str, *args, **kwargs):
        try:
            return await self._conn.execute_kw(self.model_name, method, *args, **kwargs)
        except Exception:
            logger.exception("odoo '%s' on '%s' failed", method, self.model_name)
            raise

    async def count(self, *args, **kwargs):
        return await self._exec('search_count', *args, **kwargs)

    async def search(self, *args, **kwargs):
        return await self._exec('search', *args, **kwargs)

    async def search_read(self, *args, **kwargs):
        return await self._exec('search_read', *args, **kwargs)

    async def read(self, *args, **kwargs):
        return await self._exec('read', *args, **kwargs)

    async def create(self, *args, **kwargs):
        return await self._exec('create', *args, **kwargs)


class AccountTax(OdooModel):
    model_name = 'account.tax'

    async def get_tax_id(self, tax_name: str) -> int | None:
        if self._cache.get(tax_name) is None:
            result = await self.search([[['name', '=', tax_name]]])
            if not result or not (found := int(result[0])):
                return None
            self._cache.set(tax_name, found)
        return self._cache.get_or_throw(tax_name)


class UomUom(OdooModel):
    model_name = 'uom.uom'

    async def get_unit_id(self, uom: str) -> int | None:
        if self._cache.get(uom) is None:
            result = await self.search([[['name', '=', uom]]])
            if not result or not (found := int(result[0])):
                return None
            self._cache.set(uom, found)
        return self._cache.get_or_throw(uom)


class ProductTemplate(OdooModel):
    model_name = 'product.template'

    async def exists_by_barcode(self, barcode: str) -> bool:
        return int(await self.count([[['barcode', '=', barcode]]])) > 0

    async def insert(self, *products: ProductTemplateSchema) -> list[int]:
        if not products:
            return []
        result = await self.create([[p.serialize() for p in products]])
        return result if isinstance(result, list) else [result]


class ProductProduct(OdooModel):
    model_name = 'product.product'

    async def get_product_id(self, template_id: int) -> int | None:
        if self._cache.get(template_id) is None:
            result = await self.search_read(
                [[['product_tmpl_id', '=', template_id]]],
                {'fields': ['id'], 'limit': 1},
            )
            if not result or not (found := int(result[0]['id'])):
                return None
            self._cache.set(template_id, found)
        return self._cache.get_or_throw(template_id)

    async def get_product_ids(self, template_ids: list[int]) -> dict[int, int]:
        """Variant id for every template id, resolved in a single ``search_read``.
        Shares the per-instance cache with ``get_product_id``; templates with no
        ``product.product`` row are simply absent from the result."""
        missing = [t for t in template_ids if self._cache.get(t) is None]
        if missing:
            rows = await self.search_read(
                [[['product_tmpl_id', 'in', missing]]],
                {'fields': ['id', 'product_tmpl_id']},
            )
            for r in rows:
                self._cache.set(int(r['product_tmpl_id'][0]), int(r['id']))
        return {
            t: pid for t in template_ids if (pid := self._cache.get(t)) is not None
        }


class ProductTag(OdooModel):
    model_name = 'product.tag'

    async def get_tag_id(self, tag: str) -> int | None:
        if self._cache.get(tag) is None:
            result = await self.search([[['name', '=', tag]]])
            if not result or not (found := int(result[0])):
                return None
            self._cache.set(tag, found)
        return self._cache.get_or_throw(tag)

    async def insert(self, tag: str) -> int:
        return await self.create([{'name': tag}])

    async def insert_if_not_exists(self, tag: str) -> int:
        tag_id = await self.get_tag_id(tag)
        if tag_id is None:
            tag_id = await self.insert(tag)
        return tag_id


class PosCategory(OdooModel):
    model_name = 'pos.category'

    async def get_cat_id(self, cat: str) -> int | None:
        if self._cache.get(cat) is None:
            result = await self.search([[['name', '=', cat]]])
            if not result or not (found := int(result[0])):
                return None
            self._cache.set(cat, found)
        return self._cache.get_or_throw(cat)

    async def insert(self, cat: str) -> int:
        return await self.create([{'name': cat}])

    async def insert_if_not_exists(self, cat: str) -> int:
        cat_id = await self.get_cat_id(cat)
        if cat_id is None:
            cat_id = await self.insert(cat)
        return cat_id


class ProductCategory(OdooModel):
    model_name = 'product.category'

    async def get_category_id(self, path: str) -> int | None:
        if self._cache.get(path) is None:
            result = await self.search([[['complete_name', '=', path]]])
            if not result or not (found := int(result[0])):
                return None
            self._cache.set(path, found)
        return self._cache.get_or_throw(path)

    async def insert_category(self, path: str) -> int:
        tree = path.split(_SEP)
        parent_id: int | None = None
        for i, name in enumerate(tree):
            level = _SEP.join(tree[: i + 1])
            existing = await self.get_category_id(level)
            if existing:
                parent_id = existing
            else:
                parent_id = await self.create(
                    [{'name': name, **({'parent_id': parent_id} if parent_id else {})}]
                )
        assert parent_id is not None
        return parent_id

    async def insert_if_not_exists(self, path: str) -> int:
        cat_id = await self.get_category_id(path)
        if cat_id is None:
            cat_id = await self.insert_category(path)
        return cat_id


class StockPickingType(OdooModel):
    model_name = 'stock.picking.type'

    @staticmethod
    def _key(code: str, wh_id: int) -> str:
        return f'{wh_id}:{code}'

    async def get_type_id(self, code: str, wh_id: int) -> int | None:
        key = self._key(code, wh_id)
        if self._cache.get(key) is None:
            result = await self.search(
                [[['code', '=', code], ['warehouse_id', '=', wh_id]]]
            )
            if not result or not (found := int(result[0])):
                return None
            self._cache.set(key, found)
        return self._cache.get_or_throw(key)


class StockWarehouse(OdooModel):
    model_name = 'stock.warehouse'

    def __init__(self, conn: OdooConnection):
        super().__init__(conn)
        self._locations = OdooCache()

    async def get_warehouse_id(self, name: str) -> int | None:
        if self._cache.get(name) is None:
            result = await self.search([[['name', '=', name]]])
            if not result or not (found := int(result[0])):
                return None
            self._cache.set(name, found)
        return self._cache.get_or_throw(name)

    async def get_stock_lot_id(self, wh_id: int) -> int | None:
        if self._locations.get(wh_id) is None:
            result = await self.read([[wh_id], ['lot_stock_id']])
            lot_stock_id = result[0]['lot_stock_id'][0]
            if not lot_stock_id or not (found := int(lot_stock_id)):
                return None
            self._locations.set(wh_id, found)
        return self._locations.get_or_throw(wh_id)


class StockPicking(OdooModel):
    model_name = 'stock.picking'

    async def build_for_product(
        self,
        warehouse: StockWarehouse,
        picking_type: StockPickingType,
        job_id: str,
        product_id: int,
        product: ProductTemplateSchema,
    ) -> StockPickingSchema:
        pk_type_id = await picking_type.get_type_id('internal', product.warehouse_id)
        location_id = await warehouse.get_stock_lot_id(product.warehouse_id)

        move = StockMoveSchema(
            name=product.name,
            product_id=product_id,
            product_uom_qty=1.0,
            product_uom=product.uom_id,
            location_id=location_id,
            location_dest_id=location_id,
        )

        return StockPickingSchema(
            priority=OdooPriority.Normal,
            picking_type_id=pk_type_id,
            location_id=location_id,
            location_dest_id=location_id,
            state=OdooPickingState.Done,
            scheduled_date=datetime.now(timezone.utc),
            origin=job_id,
            move_ids=[(M2MOp.Create, 0, move)],
            note='Transferencia de MMD Pawn',
        )

    async def insert(self, *pickings: StockPickingSchema) -> list[int]:
        if not pickings:
            return []
        result = await self.create([[p.serialize() for p in pickings]])
        return result if isinstance(result, list) else [result]
