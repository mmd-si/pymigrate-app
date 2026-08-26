from unittest.mock import AsyncMock, patch

from app.api.v1 import transfer as transfer_router
from app.dependencies import require_session
from app.main import app
from tests.support.builders import make_job_error, make_job_item, make_session, make_transfer_job


async def test_index_non_empty_uses_found_message(app_client):
    app.dependency_overrides[require_session] = lambda: make_session(user_id='user-1')
    job = make_transfer_job(owner_id='user-1', errors=[], items=[])

    with patch.object(transfer_router.transfer, 'list_summary', new=AsyncMock(return_value=[
        transfer_router.JobSummary.from_populated(job)
    ])):
        response = await app_client.get('/api/v1/transfers/')

    assert response.status_code == 200
    assert response.json()['message'] == 'La lista de transferencias fue encontrada con éxito.'


async def test_index_empty_uses_no_results_message(app_client):
    app.dependency_overrides[require_session] = lambda: make_session(user_id='user-1')

    with patch.object(transfer_router.transfer, 'list_summary', new=AsyncMock(return_value=[])):
        response = await app_client.get('/api/v1/transfers/')

    assert response.status_code == 200
    assert response.json()['message'] == 'La operación fue realizada con éxito, pero no hay resultados que retornar.'


async def test_index_clamps_limit_and_passes_user_id(app_client):
    app.dependency_overrides[require_session] = lambda: make_session(user_id='user-42')

    with patch.object(transfer_router.transfer, 'list_summary', new=AsyncMock(return_value=[])) as list_summary:
        await app_client.get('/api/v1/transfers/', params={'limit': 500, 'offset': -5})

    args = list_summary.call_args.args
    assert args[1] == 'user-42'
    assert args[2] == 100
    assert args[3] == 0


async def test_show_returns_detailed_job_when_found(app_client):
    job = make_transfer_job(items=[], errors=[])
    from app.schemas.response import DetailedJob
    detailed = DetailedJob.from_populated(job, inventory={})

    with patch.object(transfer_router.transfer, 'detailed', new=AsyncMock(return_value=detailed)):
        response = await app_client.get(f'/api/v1/transfers/{job.job_id}')

    assert response.status_code == 200
    assert response.json()['data']['job_id'] == job.job_id


async def test_show_returns_404_when_not_found(app_client):
    with patch.object(transfer_router.transfer, 'detailed', new=AsyncMock(return_value=None)):
        response = await app_client.get('/api/v1/transfers/missing')

    assert response.status_code == 404


async def test_pdf_returns_404_before_rendering_when_job_not_found(app_client):
    with patch.object(transfer_router.transfer, 'detailed', new=AsyncMock(return_value=None)), \
         patch.object(transfer_router.report, 'transfer_pdf', new=AsyncMock()) as transfer_pdf:
        response = await app_client.get('/api/v1/transfers/missing/pdf')

    assert response.status_code == 404
    transfer_pdf.assert_not_called()


async def test_pdf_returns_bytes_with_correct_headers(app_client):
    job = make_transfer_job(items=[], errors=[])
    from app.schemas.response import DetailedJob
    detailed = DetailedJob.from_populated(job, inventory={})

    with patch.object(transfer_router.transfer, 'detailed', new=AsyncMock(return_value=detailed)), \
         patch.object(transfer_router.report, 'transfer_pdf', new=AsyncMock(return_value=b'%PDF-1.4')):
        response = await app_client.get(f'/api/v1/transfers/{job.job_id}/pdf')

    assert response.status_code == 200
    assert response.headers['content-type'] == 'application/pdf'
    assert response.headers['content-disposition'] == f'inline; filename="transfer-{job.job_id}.pdf"'
    assert response.content == b'%PDF-1.4'


async def test_pdf_render_failure_surfaces_as_generic_500(app_client):
    job = make_transfer_job(items=[], errors=[])
    from app.schemas.response import DetailedJob
    detailed = DetailedJob.from_populated(job, inventory={})

    with patch.object(transfer_router.transfer, 'detailed', new=AsyncMock(return_value=detailed)), \
         patch.object(transfer_router.report, 'transfer_pdf', new=AsyncMock(side_effect=RuntimeError('boom'))):
        response = await app_client.get(f'/api/v1/transfers/{job.job_id}/pdf')

    assert response.status_code == 500
    assert response.json() == {'detail': 'Hubo un error inesperado.'}


async def test_create_returns_400_and_skips_service_call_when_row_ids_empty(app_client):
    with patch.object(transfer_router.transfer, 'create', new=AsyncMock()) as create:
        response = await app_client.post('/api/v1/transfers/', json={'rowIds': []})

    assert response.status_code == 400
    assert response.json()['detail'] == 'Orden de trabajo vacía.'
    create.assert_not_called()


async def test_create_returns_400_when_all_barcodes_invalid(app_client):
    with patch.object(transfer_router.transfer, 'create', new=AsyncMock(return_value=None)):
        response = await app_client.post('/api/v1/transfers/', json={'rowIds': ['BC001']})

    assert response.status_code == 400
    assert response.json()['detail'] == 'Todos los códigos enviados fueron inválidos.'


async def test_create_returns_202_with_job_id_on_success(app_client):
    app.dependency_overrides[require_session] = lambda: make_session(user_id='user-9')

    with patch.object(transfer_router.transfer, 'create', new=AsyncMock(return_value='job-123')) as create:
        response = await app_client.post('/api/v1/transfers/', json={'rowIds': ['BC001', 'BC002']})

    assert response.status_code == 202
    assert response.json()['data'] == 'job-123'
    args = create.call_args.args
    assert args[2] == ['BC001', 'BC002']
    assert args[3] == 'user-9'
