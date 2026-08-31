"""Async Odoo XML-RPC client and per-model wrappers, ported from
``pymigrate/migrate-worker/app/odoo/*``.

``OdooContext`` bundles one authenticated connection with a fresh set of model
wrappers (each with its own lookup cache). Build one per drain cycle so cached
master-data ids never go stale across cycles.
"""

from dataclasses import dataclass

from app.config.settings import Settings
from app.odoo.connection import OdooConnection
from app.odoo.models import (
    AccountTax,
    PosCategory,
    ProductCategory,
    ProductProduct,
    ProductTag,
    ProductTemplate,
    StockPicking,
    StockPickingType,
    StockWarehouse,
    UomUom,
)


@dataclass
class OdooContext:
    connection: OdooConnection
    product_template: ProductTemplate
    product_product: ProductProduct
    product_category: ProductCategory
    pos_category: PosCategory
    product_tag: ProductTag
    account_tax: AccountTax
    uom_uom: UomUom
    stock_warehouse: StockWarehouse
    stock_picking: StockPicking
    stock_picking_type: StockPickingType

    @classmethod
    async def create(cls, settings: Settings) -> 'OdooContext':
        conn = OdooConnection(settings)
        await conn.ensure()
        return cls(
            connection=conn,
            product_template=ProductTemplate(conn),
            product_product=ProductProduct(conn),
            product_category=ProductCategory(conn),
            pos_category=PosCategory(conn),
            product_tag=ProductTag(conn),
            account_tax=AccountTax(conn),
            uom_uom=UomUom(conn),
            stock_warehouse=StockWarehouse(conn),
            stock_picking=StockPicking(conn),
            stock_picking_type=StockPickingType(conn),
        )


__all__ = ['OdooContext', 'OdooConnection']
