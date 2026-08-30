"""Map a validated ``JoinedItem`` to a ``ProductTemplateSchema``, resolving /
creating all the Odoo master data it references (uom, tag, warehouse, product
category tree, pos category, taxes) along the way.

Ported from ``pymigrate/migrate-worker/app/pipes/mapper.py``, made async. Category
resolution reuses the app's existing ``app.core.resolvers.procedural_resolver``
(the worker's own ``resolve_category`` was dropped in favour of it). ``JoinedItem``
duck-types the ``.description`` / ``.pawn_type`` / ``.carat_rating`` attributes it
reads.
"""

import logging
import secrets

from app.config.settings import Settings
from app.core.resolvers import procedural_resolver
from app.schemas.odoo import (
    JoinedItem,
    M2MOp,
    OdooProductType,
    ProductTemplateSchema,
)
from app.odoo import OdooContext

logger = logging.getLogger(__name__)


def resolve_name(item: JoinedItem) -> str:
    def trim(x: str | None) -> str:
        return (x or '').strip()

    return (
        ' '.join(
            w
            for w in [
                trim(item.description).title(),
                trim(item.carat_rating),
                'grs.' if item.weight and item.weight > 0 else '',
            ]
            if w
        )
        or ' - '.join(
            w for w in [trim(item.pawn_type), trim(item.observations), trim(item.barcode)] if w
        ).lower()
        or ''
    )


class Mapper:
    @staticmethod
    async def map(
        odoo: OdooContext, item: JoinedItem, settings: Settings
    ) -> ProductTemplateSchema:
        uom_id = await odoo.uom_uom.get_unit_id('Units')
        tag_id = await odoo.product_tag.insert_if_not_exists('LOGICA DE ETIQUETAS')
        wh_id = await odoo.stock_warehouse.get_warehouse_id(item.branch)
        cat_id = await odoo.product_category.insert_if_not_exists(procedural_resolver(item))
        pos_cat_id = await odoo.pos_category.get_cat_id((item.branch or '').upper())
        supplier_tax_id = await odoo.account_tax.get_tax_id('ITBMS Compra')
        customer_tax_id = await odoo.account_tax.get_tax_id('ITBMS Venta')

        barcode = (
            f'{item.barcode}?{secrets.token_hex(8)}'
            if settings.odoo_fake_barcodes
            else item.barcode
        )

        return ProductTemplateSchema(
            default_code=barcode,
            barcode=barcode,
            name=resolve_name(item),
            uom_id=uom_id,
            uom_po_id=uom_id,
            weight=item.weight,
            sale_ok=True,
            purchase_ok=False,
            available_in_pos=True,
            pos_categ_ids=[(M2MOp.Replace, 0, [pos_cat_id])],
            type=OdooProductType.Goods,
            supplier_taxes_id=[(M2MOp.Replace, 0, [supplier_tax_id])],
            taxes_id=[(M2MOp.Replace, 0, [customer_tax_id])],
            product_tag_ids=[(M2MOp.Replace, 0, [tag_id])],
            list_price=item.retail_price,
            standard_price=item.cost,
            description=item.observations,
            warehouse_id=wh_id,
            categ_id=cat_id,
        )
