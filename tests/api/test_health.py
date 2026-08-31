from unittest.mock import AsyncMock

from sqlalchemy.exc import SQLAlchemyError

from app.dependencies import get_local_db, get_remote_db
from app.main import app


async def _failing_db():
    db = AsyncMock()
    db.execute.side_effect = SQLAlchemyError('down')
    yield db


async def test_health_both_dbs_ok_returns_success_message(app_client):
    response = await app_client.get('/api/health')

    assert response.status_code == 200
    body = response.json()
    assert body['type'] == 'success'
    assert body['message'] == 'Todos los sistemas operativos'


async def test_health_local_db_failure_returns_local_warning_503(app_client):
    app.dependency_overrides[get_local_db] = _failing_db

    response = await app_client.get('/api/health')

    assert response.status_code == 503
    assert response.json()['message'] == 'Base de datos local inaccesible'


async def test_health_remote_db_failure_returns_remote_warning(app_client):
    app.dependency_overrides[get_remote_db] = _failing_db

    response = await app_client.get('/api/health')

    assert response.status_code == 503
    assert response.json()['message'] == 'Base de datos remota inaccesible'


async def test_health_both_failing_local_warning_takes_precedence(app_client):
    app.dependency_overrides[get_local_db] = _failing_db
    app.dependency_overrides[get_remote_db] = _failing_db

    response = await app_client.get('/api/health')

    assert response.status_code == 503
    assert response.json()['message'] == 'Base de datos local inaccesible'


async def test_health_mmdpawn_failure_returns_mmdpawn_warning(app_client, mock_mmdpawn_api):
    mock_mmdpawn_api.side_effect = ConnectionError('unreachable')

    response = await app_client.get('/api/health')

    assert response.status_code == 503
    assert response.json()['message'] == 'API de MMD Pawn inaccesible'
