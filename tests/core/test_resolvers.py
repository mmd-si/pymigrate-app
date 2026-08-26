from types import SimpleNamespace

from app.core.resolvers import procedural_resolver


def _row(description=None, pawn_type=None, carat_rating=None):
    return SimpleNamespace(description=description, pawn_type=pawn_type, carat_rating=carat_rating)


def test_oro_with_carat_and_valuable_keyword():
    row = _row(description='Anillo de oro macizo', pawn_type='oro', carat_rating='14K')
    assert procedural_resolver(row) == 'Oro / 14K / Anillo'


def test_oro_with_brillante_keyword():
    row = _row(description='Anillo con brillante', pawn_type='oro')
    assert procedural_resolver(row) == 'Oro / Brillante / Anillo'


def test_plata_never_gets_brillante_segment():
    row = _row(description='Pulsera de plata con brillante', pawn_type='plata', carat_rating='0.925')
    assert procedural_resolver(row) == 'Plata / 0925 / Pulsera'


def test_oro_no_valuable_keyword_falls_back_to_varios():
    row = _row(description='articulo raro sin match', pawn_type='oro')
    assert procedural_resolver(row) == 'Oro / Varios'


def test_reloj_keyword_in_description():
    row = _row(description='Reloj Rolex usado')
    assert procedural_resolver(row) == 'Relojes Usados / Reloj'


def test_default_branch_tools_keyword():
    row = _row(description='Taladro Bosch')
    assert procedural_resolver(row) == 'Artículos Usados / Herramientas'


def test_default_branch_electronics_keyword():
    row = _row(description='Celular Samsung')
    assert procedural_resolver(row) == 'Artículos Usados / Electrónicos'


def test_default_branch_no_keyword_falls_back_to_varios():
    row = _row(description='Objeto random')
    assert procedural_resolver(row) == 'Artículos Usados / Varios'


def test_matching_is_case_insensitive():
    row = _row(description='ANILLO DE ORO', pawn_type='ORO')
    assert procedural_resolver(row) == 'Oro / Anillo'
