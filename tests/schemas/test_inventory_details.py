from app.schemas.response import InventoryDetails
from tests.support.builders import make_inventory_row


def test_branch_strips_masmedan_and_collapses_whitespace():
    details = InventoryDetails.from_row(make_inventory_row(branch='MASMEDAN   Sucursal Uno'))
    assert details.branch == 'Sucursal Uno'


def test_branch_empty_when_raw_branch_falsy():
    details = InventoryDetails.from_row(make_inventory_row(branch=None))
    assert details.branch == ''


def test_raw_branch_excluded_from_serialized_output():
    details = InventoryDetails.from_row(make_inventory_row(branch='MASMEDAN Sucursal Uno'))
    dumped = details.model_dump()
    assert 'raw_branch' not in dumped
    assert dumped['branch'] == 'Sucursal Uno'


def test_name_combines_description_carat_weight_and_suffix():
    details = InventoryDetails.from_row(make_inventory_row(
        description='anillo de oro', carat_rating='14K', weight=5.0,
        pawn_type='Empeño', observations='Bueno', barcode='BC001',
    ))
    assert details.name == 'Anillo De Oro 14K 5.0grs. empeño-bueno-bc001'


def test_name_is_none_when_all_inputs_missing():
    details = InventoryDetails.from_row(make_inventory_row(
        description=None, carat_rating=None, weight=None,
        pawn_type=None, observations=None, barcode=None,
    ))
    assert details.name is None


def test_product_category_delegates_to_procedural_resolver():
    details = InventoryDetails.from_row(make_inventory_row(
        description='Anillo de oro', pawn_type='oro', carat_rating='14K',
    ))
    assert details.product_category == 'Oro / 14K / Anillo'


def test_from_row_maps_fixed_literal_fields():
    details = InventoryDetails.from_row(make_inventory_row())
    assert details.uom == 'Unidades'
    assert details.purchase_uom == 'Unidades'
    assert details.can_be_sold is True
    assert details.can_be_bought is False
    assert details.product_type == 'Producto almacenable'
    assert details.provider_tax == 'ITBMS'
    assert details.customer_tax == 'ITBMS'


def test_from_row_maps_row_derived_fields():
    row = make_inventory_row(barcode='BC999', retail_price=250.0, cost=100.0)
    details = InventoryDetails.from_row(row)
    assert details.internal_ref == 'BC999'
    assert details.barcode == 'BC999'
    assert details.retail_price == 250.0
    assert details.cost == 100.0
