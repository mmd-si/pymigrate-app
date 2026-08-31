from app.pipes.normalizer import Normalizer, branch_title, noneif_na, trimstr
from app.schemas.odoo import JoinedItem
from tests.support.builders import make_source_row


def test_normalize_maps_and_cleans_row():
    row = make_source_row(
        barcode='  BC001 ',
        description='  Anillo   de   oro ',
        weight='5.0',
        retail_price='100',
        cost='50',
        brand='N/A',
        carat_rating='14k',
        branch='MASMEDAN sucursal uno',
    )

    item = Normalizer.normalize(row)

    assert isinstance(item, JoinedItem)
    assert item.barcode == 'BC001'
    assert item.description == 'Anillo de oro'
    assert item.weight == 5.0 and isinstance(item.weight, float)
    assert item.retail_price == 100.0
    assert item.cost == 50.0
    assert item.brand is None  # 'N/A' -> None
    assert item.carat_rating == '14K'
    assert item.branch == 'Sucursal Uno'  # MASMEDAN stripped, title-cased


def test_normalize_passes_none_numerics_through():
    item = Normalizer.normalize(make_source_row(weight=None, cost=None, stone_weight=None))
    assert item.weight is None
    assert item.cost is None
    assert item.stone_weight is None


def test_helpers():
    assert noneif_na('n/a') is None
    assert noneif_na('  x ') == 'x'
    assert trimstr(None) == ''
    assert trimstr('  a  b ') == 'a b'
    assert branch_title('MASMEDAN foo') == ' Foo'
