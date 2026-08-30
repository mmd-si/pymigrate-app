from datetime import datetime, timezone

from app.schemas.odoo import (
    OdooPickingState,
    OdooPriority,
    OdooProductType,
    ProductTemplateSchema,
    StockPickingSchema,
)
from app.odoo.models import (
    ProductCategory,
    ProductProduct,
    ProductTemplate,
    StockWarehouse,
    UomUom,
)


class FakeConn:
    def __init__(self, responder):
        self.calls: list[tuple] = []
        self._responder = responder

    async def ensure(self):
        pass

    async def execute_kw(self, model, method, *args, **kwargs):
        self.calls.append((model, method, args))
        return self._responder(model, method, args)


async def test_lookup_caches_and_hits_odoo_once():
    conn = FakeConn(lambda *_: [42])
    uom = UomUom(conn)

    assert await uom.get_unit_id('Units') == 42
    assert await uom.get_unit_id('Units') == 42
    assert len(conn.calls) == 1  # second call served from cache


async def test_lookup_returns_none_on_empty():
    conn = FakeConn(lambda *_: [])
    assert await UomUom(conn).get_unit_id('Nope') is None


async def test_product_product_reads_variant_id():
    conn = FakeConn(lambda *_: [{'id': 9}])
    assert await ProductProduct(conn).get_product_id(3) == 9


async def test_product_category_creates_missing_levels_with_parent():
    created: list[dict] = []

    def responder(model, method, args):
        if method == 'search':
            return []  # nothing exists
        if method == 'create':
            created.append(args[0][0])
            return len(created)  # 1, then 2
        raise AssertionError(method)

    cat = ProductCategory(conn := FakeConn(responder))
    leaf = await cat.insert_if_not_exists('Oro / 14K')

    assert leaf == 2
    assert created[0] == {'name': 'Oro'}
    assert created[1] == {'name': '14K', 'parent_id': 1}


async def test_stock_warehouse_lot_stock_id():
    conn = FakeConn(lambda m, meth, a: [{'lot_stock_id': [17, 'Stock']}])
    assert await StockWarehouse(conn).get_stock_lot_id(5) == 17


async def test_product_template_insert_serializes_batch():
    conn = FakeConn(lambda *_: [101])
    tmpl = ProductTemplate(conn)
    schema = ProductTemplateSchema(
        default_code='BC1', barcode='BC1', name='X', uom_id=1, uom_po_id=1,
        weight=2.0, sale_ok=True, purchase_ok=False, available_in_pos=True,
        pos_categ_ids=[(6, 0, [1])], type=OdooProductType.Goods,
        supplier_taxes_id=[(6, 0, [2])], taxes_id=[(6, 0, [3])],
        product_tag_ids=[(6, 0, [4])], list_price=10.0, standard_price=5.0,
        description=None, warehouse_id=1, categ_id=1,
    )

    ids = await tmpl.insert(schema)

    assert ids == [101]
    model, method, args = conn.calls[0]
    assert (model, method) == ('product.template', 'create')
    payload = args[0][0][0]
    assert payload['type'] == 'consu'
    assert 'description' not in payload  # None dropped by serialize()


def test_stock_picking_schema_serializes_nested_move():
    picking = StockPickingSchema(
        priority=OdooPriority.Normal, picking_type_id=1, location_id=2,
        state=OdooPickingState.Done, location_dest_id=2,
        scheduled_date=datetime(2026, 1, 1, tzinfo=timezone.utc), origin='job-1',
        move_ids=[], note='n',
    )
    data = picking.serialize()
    assert data['priority'] == '0'
    assert data['state'] == 'done'
    assert data['scheduled_date'] == '2026-01-01 00:00:00'
    assert 'partner_id' not in data
