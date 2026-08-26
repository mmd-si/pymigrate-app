from app.schemas.response import SimpleSession
from tests.support.builders import make_session


def test_simple_session_round_trips_first_and_last_name():
    session = make_session(first_name='Ana', last_name='Gómez')

    simple = SimpleSession.from_session(session)

    assert simple.first_name == 'Ana'
    assert simple.last_name == 'Gómez'


def test_simple_session_round_trips_remaining_fields():
    session = make_session(
        user_id='user-42', branch_id=826, role_id=2,
        ip_address='10.0.0.1', user_agent='UA', data={'foo': 'bar'},
    )

    simple = SimpleSession.from_session(session)

    assert simple.user_id == 'user-42'
    assert simple.branch_id == 826
    assert simple.role_id == 2
    assert simple.ip_address == '10.0.0.1'
    assert simple.user_agent == 'UA'
    assert simple.data == {'foo': 'bar'}
