from fastapi import APIRouter, HTTPException, Response
from app.core.utils import clamp
from app.dependencies import RequiresLocalDB, RequiresRemoteDB, RequiresSession
from app.schemas.internal import ListResponse, ItemResponse
from app.schemas.request import TransferRequest
from app.schemas.response import DetailedJob, JobSummary
from app.services import report, transfer


router = APIRouter(prefix='/transfers')


@router.get('/', response_model=ListResponse[JobSummary])
async def index(db: RequiresLocalDB, current: RequiresSession, limit: int = 20, offset: int = 0):
    limit = clamp(limit, 0, 100)
    offset = max(0, offset)

    jobs = await transfer.list_summary(db, current.user_id, limit, offset)

    message = (
         'La lista de transferencias fue encontrada con éxito.'
         if jobs else
         'La operación fue realizada con éxito, pero no hay resultados que retornar.'
    )

    return ListResponse(message=message, data=jobs)

@router.get('/{job_id}', response_model=ItemResponse[DetailedJob])
async def show(lcl: RequiresLocalDB, rmt: RequiresRemoteDB, current: RequiresSession, job_id: str):
        job = await transfer.detailed(lcl, rmt, job_id, current.user_id)
        if job is None:
            raise HTTPException(404, 'No se encontró la transferencia.')
        return ItemResponse(message='La transferencia fue encontrada con éxito.', data=job)


@router.post('/', status_code=202, response_model=ItemResponse[str])
async def create(lcl: RequiresLocalDB, rmt: RequiresRemoteDB, current: RequiresSession, data: TransferRequest):
    if not data.row_ids:
         raise HTTPException(400, 'Orden de trabajo vacía.')
    job_id = await transfer.create(lcl, rmt, data.row_ids, current.user_id)
    if job_id is None:
         raise HTTPException(400, 'Todos los códigos enviados fueron inválidos.')
    return ItemResponse(
        message='La transferencia fue registrada con éxito. Se ejecutará en el próximo ciclo.',
        data=job_id
    )

@router.get('/{job_id}/pdf', response_model=None)
async def export(lcl: RequiresLocalDB, rmt: RequiresRemoteDB, current: RequiresSession, job_id: str):
    job = await transfer.detailed(lcl, rmt, job_id, current.user_id)
    if job is None:
        raise HTTPException(404, 'No se encontró la transferencia.')
    pdf = await report.transfer_pdf(job)
    return Response(
        content=pdf,
        media_type='application/pdf',
        headers={'Content-Disposition': f'inline; filename="transfer-{job.job_id}.pdf"'}
    )
