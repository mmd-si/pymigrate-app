import pytest

from app.config.settings import get_settings
from app.pipes.mapper import Mapper, resolve_name
from app.schemas.odoo import JoinedItem, M2MOp, OdooProductType
from tests.support.builders import make_odoo_context


def _item(**overrides) -> JoinedItem:
    defaults = dict(
        barcode='BC001', description='Anillo de oro', weight=5.0, retail_price=100.0,
        cost=50.0, observations='sin piedras', pawn_no='EMP-1', stone_weight=None,
        brand=None, model=None, series=None, carat_rating='14K', pawn_type='oro',
        branch='Sucursal Uno',
    )
    defaults.update(overrides)
    return JoinedItem(**defaults)


def test_resolve_name_primary_form():
    assert resolve_name(_item()) == 'Anillo De Oro 14K grs.'


def test_resolve_name_fallback_when_no_description():
    name = resolve_name(_item(description=None, weight=None, carat_rating=None))
    assert name == 'oro - sin piedras - bc001'


async def test_map_builds_product_template_payload():
    odoo = make_odoo_context()
    odoo.uom_uom.get_unit_id.return_value = 7
    odoo.product_tag.insert_if_not_exists.return_value = 3
    odoo.stock_warehouse.get_warehouse_id.return_value = 11
    odoo.product_category.insert_if_not_exists.return_value = 22
    odoo.pos_category.get_cat_id.return_value = 33
    odoo.account_tax.get_tax_id.side_effect = (
        lambda name: {'ITBMS Compra': 44, 'ITBMS Venta': 55}[name]
    )

    product = await Mapper.map(odoo, _item(), get_settings())

    assert product.barcode == 'BC001' and product.default_code == 'BC001'
    assert product.name == 'Anillo De Oro 14K grs.'
    assert product.uom_id == 7 and product.uom_po_id == 7
    assert product.warehouse_id == 11 and product.categ_id == 22
    # category path comes from the app's existing procedural_resolver
    odoo.product_category.insert_if_not_exists.assert_awaited_once_with('Oro / 14K / Anillo')
    assert product.type is OdooProductType.Goods
    assert product.list_price == 100.0 and product.standard_price == 50.0

    payload = product.serialize()
    assert payload['type'] == 'consu'
    assert payload['taxes_id'] == [(M2MOp.Replace, 0, [55])]
    assert payload['supplier_taxes_id'] == [(M2MOp.Replace, 0, [44])]
    assert payload['pos_categ_ids'] == [(M2MOp.Replace, 0, [33])]
    assert payload['product_tag_ids'] == [(M2MOp.Replace, 0, [3])]


async def test_map_fake_barcode_suffix_toggle(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, 'odoo_fake_barcodes', True)

    odoo = make_odoo_context()
    for m in (
        odoo.uom_uom.get_unit_id, odoo.product_tag.insert_if_not_exists,
        odoo.stock_warehouse.get_warehouse_id,
        odoo.product_category.insert_if_not_exists, odoo.pos_category.get_cat_id,
        odoo.account_tax.get_tax_id,
    ):
        m.return_value = 1

    product = await Mapper.map(odoo, _item(), settings)
    assert product.barcode.startswith('BC001?')
