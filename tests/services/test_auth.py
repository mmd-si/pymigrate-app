import urllib.parse
from datetime import timedelta
from unittest.mock import AsyncMock

from app.services import auth
from app.core.utils import utcnow
from tests.support.builders import make_external_auth, make_session, mock_db, mock_result


def test_session_ttl_remember_me_true_is_30_days():
    assert auth.session_ttl(True) == timedelta(days=30)


def test_session_ttl_remember_me_false_is_7_days():
    assert auth.session_ttl(False) == timedelta(days=7)


async def test_create_session_stores_hashed_pysessid_but_returns_plaintext(monkeypatch):
    db = mock_db()
    monkeypatch.setattr(auth.secrets, 'token_urlsafe', lambda n: 'plaintext-token')

    from app.schemas.external import ExternalAuth
    data = ExternalAuth.model_validate(make_external_auth())

    pysessid = await auth.create_session(db, data, ip_address='1.2.3.4', user_agent='UA', ttl=3600)

    assert pysessid == 'plaintext-token'
    db.add.assert_called_once()
    stored = db.add.call_args.args[0]
    assert stored.pysessid == auth.crypto.sha256hash('plaintext-token')
    assert stored.pysessid != 'plaintext-token'
    db.flush.assert_awaited_once()


async def test_create_session_maps_fields_from_external_auth():
    db = mock_db()
    data_dict = make_external_auth(info_overrides={'idSucursal': '826', 'idPerfil': '2', 'nombre': 'Ana', 'apellido': 'Gómez'}, login_overrides={'idLogin': '999'})
    from app.schemas.external import ExternalAuth
    data = ExternalAuth.model_validate(data_dict)

    await auth.create_session(db, data, ip_address='1.2.3.4', user_agent='UA', ttl=3600)

    stored = db.add.call_args.args[0]
    assert stored.user_id == '999'
    assert stored.branch_id == 826
    assert stored.role_id == 2
    assert stored.first_name == 'Ana'
    assert stored.last_name == 'Gómez'
    assert stored.ip_address == '1.2.3.4'
    assert stored.user_agent == 'UA'


async def test_revoke_session_executes_delete_and_flushes():
    db = AsyncMock()

    await auth.revoke_session(db, 'some-token')

    db.execute.assert_awaited_once()
    db.flush.assert_awaited_once()


async def test_find_session_returns_non_expired_session_without_revoking(monkeypatch):
    db = AsyncMock()
    session = make_session(expires_at=utcnow() + timedelta(days=1))
    db.execute.return_value = mock_result(scalar_one_or_none=session)
    revoke = AsyncMock()
    monkeypatch.setattr(auth, 'revoke_session', revoke)

    result = await auth.find_session(db, 'token')

    assert result is session
    revoke.assert_not_called()


async def test_find_session_revokes_and_returns_none_when_expired(monkeypatch):
    db = AsyncMock()
    session = make_session(expires_at=utcnow() - timedelta(days=1))
    db.execute.return_value = mock_result(scalar_one_or_none=session)
    revoke = AsyncMock()
    monkeypatch.setattr(auth, 'revoke_session', revoke)

    result = await auth.find_session(db, 'token')

    assert result is None
    revoke.assert_awaited_once_with(db, 'token')


async def test_find_session_returns_none_when_not_found():
    db = AsyncMock()
    db.execute.return_value = mock_result(scalar_one_or_none=None)

    result = await auth.find_session(db, 'token')

    assert result is None


def test_mmdpawn_encrypt_decrypt_round_trip():
    ciphertext = auth.mmdpawn_encrypt('secret-password')
    assert auth.mmdpawn_decrypt(urllib.parse.quote(ciphertext)) == 'secret-password'
