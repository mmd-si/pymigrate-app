import pytest

from app.pipes.errors import ValidationError
from app.pipes.validator import Validator
from app.schemas.odoo import JoinedItem


def _item(**overrides) -> JoinedItem:
    defaults = dict(
        barcode='BC001', description='Anillo', weight=1.0, retail_price=10.0,
        cost=5.0, observations=None, pawn_no=None, stone_weight=None, brand=None,
        model=None, series=None, carat_rating=None, pawn_type='oro', branch='X',
    )
    defaults.update(overrides)
    return JoinedItem(**defaults)


def test_valid_item_passes_through_unchanged():
    item = _item()
    assert Validator.validate(item) is item


def test_missing_barcode_raises():
    with pytest.raises(ValidationError, match='código de barra'):
        Validator.validate(_item(barcode=None))


def test_negative_numbers_raise_and_accumulate():
    with pytest.raises(ValidationError) as excinfo:
        Validator.validate(_item(weight=-1.0, cost=-2.0))
    assert 'peso' in str(excinfo.value)
    assert 'costo' in str(excinfo.value)


def test_none_numbers_are_allowed():
    Validator.validate(_item(weight=None, retail_price=None, cost=None, stone_weight=None))
