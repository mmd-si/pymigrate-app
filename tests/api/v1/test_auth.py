from unittest.mock import AsyncMock, MagicMock, patch

from app.api.v1 import auth as auth_router
from app.dependencies import require_session
from app.main import app
from tests.support.builders import make_external_auth, make_session


def _requests_response(json_body: dict) -> MagicMock:
    response = MagicMock()
    response.json.return_value = json_body
    return response


async def test_login_success_sets_cookie_and_creates_session(app_client):
    fake_requests = MagicMock()
    fake_requests.get.return_value = _requests_response(make_external_auth())
    create_session = AsyncMock(return_value='plaintext-token')

    with patch.object(auth_router, 'requests', fake_requests), \
         patch.object(auth_router.auth, 'create_session', create_session):
        response = await app_client.post('/api/v1/auth/login', json={
            'username': 'user1', 'password': 'pass1', 'rememberMe': False,
        })

    assert response.status_code == 200
    assert response.json()['message'] == 'Autenticación exitosa'
    assert 'pysessid=plaintext-token' in response.headers.get('set-cookie', '')
    create_session.assert_awaited_once()


async def test_login_sends_encrypted_credentials_to_mmdpawn(app_client):
    fake_requests = MagicMock()
    fake_requests.get.return_value = _requests_response(make_external_auth())

    with patch.object(auth_router, 'requests', fake_requests), \
         patch.object(auth_router.auth, 'create_session', AsyncMock(return_value='tok')):
        await app_client.post('/api/v1/auth/login', json={
            'username': 'plainuser', 'password': 'plainpass', 'rememberMe': False,
        })

    params = fake_requests.get.call_args.kwargs['params']
    assert params['usuario'] != 'plainuser'
    assert params['clave'] != 'plainpass'
    from app.services import auth as auth_service
    assert auth_service.mmdpawn_decrypt(params['usuario']) == 'plainuser'


async def test_login_returns_401_when_continuar_is_not_1(app_client):
    fake_requests = MagicMock()
    fake_requests.get.return_value = _requests_response(make_external_auth(continuar=0))

    with patch.object(auth_router, 'requests', fake_requests):
        response = await app_client.post('/api/v1/auth/login', json={
            'username': 'u', 'password': 'p', 'rememberMe': False,
        })

    assert response.status_code == 401


async def test_login_returns_401_when_datos_is_a_string(app_client):
    fake_requests = MagicMock()
    fake_requests.get.return_value = _requests_response(make_external_auth(datos='credenciales incorrectas'))

    with patch.object(auth_router, 'requests', fake_requests):
        response = await app_client.post('/api/v1/auth/login', json={
            'username': 'u', 'password': 'p', 'rememberMe': False,
        })

    assert response.status_code == 401


async def test_login_external_api_failure_surfaces_as_generic_500(app_client):
    fake_requests = MagicMock()
    fake_requests.get.side_effect = ConnectionError('unreachable')

    with patch.object(auth_router, 'requests', fake_requests):
        response = await app_client.post('/api/v1/auth/login', json={
            'username': 'u', 'password': 'p', 'rememberMe': False,
        })

    assert response.status_code == 500
    assert response.json() == {'detail': 'Hubo un error inesperado.'}


async def test_login_remember_me_true_uses_30_day_ttl(app_client):
    fake_requests = MagicMock()
    fake_requests.get.return_value = _requests_response(make_external_auth())
    create_session = AsyncMock(return_value='tok')

    with patch.object(auth_router, 'requests', fake_requests), \
         patch.object(auth_router.auth, 'create_session', create_session):
        await app_client.post('/api/v1/auth/login', json={
            'username': 'u', 'password': 'p', 'rememberMe': True,
        })

    assert create_session.call_args.kwargs['ttl'] == 30 * 24 * 3600


async def test_login_remember_me_false_uses_7_day_ttl(app_client):
    fake_requests = MagicMock()
    fake_requests.get.return_value = _requests_response(make_external_auth())
    create_session = AsyncMock(return_value='tok')

    with patch.object(auth_router, 'requests', fake_requests), \
         patch.object(auth_router.auth, 'create_session', create_session):
        await app_client.post('/api/v1/auth/login', json={
            'username': 'u', 'password': 'p', 'rememberMe': False,
        })

    assert create_session.call_args.kwargs['ttl'] == 7 * 24 * 3600


async def test_session_returns_not_authenticated_when_no_cookie(app_client):
    response = await app_client.get('/api/v1/auth/session')

    assert response.status_code == 200
    body = response.json()
    assert body['data'] is None
    assert body['message'] == 'No autenticado'


async def test_session_returns_not_authenticated_when_session_invalid(app_client):
    with patch.object(auth_router.auth, 'find_session', new=AsyncMock(return_value=None)):
        response = await app_client.get('/api/v1/auth/session', headers={'Cookie': 'pysessid=bogus'})

    body = response.json()
    assert body['data'] is None
    assert body['message'] == 'No autenticado'


async def test_session_returns_session_data_when_valid(app_client):
    session = make_session(user_id='user-1', branch_id=826)
    with patch.object(auth_router.auth, 'find_session', new=AsyncMock(return_value=session)):
        response = await app_client.get('/api/v1/auth/session', headers={'Cookie': 'pysessid=valid'})

    body = response.json()
    assert body['message'] == 'Autenticado.'
    assert body['data']['user_id'] == 'user-1'
    assert body['data']['branch_id'] == 826


async def test_logout_without_cookie_does_not_call_revoke(app_client):
    with patch.object(auth_router.auth, 'revoke_session', new=AsyncMock()) as revoke:
        response = await app_client.post('/api/v1/auth/logout')

    assert response.status_code == 200
    revoke.assert_not_called()


async def test_logout_with_cookie_revokes_session_and_clears_cookie(app_client):
    with patch.object(auth_router.auth, 'revoke_session', new=AsyncMock()) as revoke:
        response = await app_client.post('/api/v1/auth/logout', headers={'Cookie': 'pysessid=tok123'})

    assert response.status_code == 200
    revoke.assert_awaited_once()
    assert revoke.call_args.args[1] == 'tok123'
    set_cookie = response.headers.get('set-cookie', '')
    assert 'pysessid=' in set_cookie
    assert 'Max-Age=0' in set_cookie
