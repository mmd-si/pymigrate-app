from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.core.utils import utcnow
from app.models.local import (
    ItemResult,
    JobResult,
    JobStatus,
    Session,
    TransferJob,
    TransferJobError,
    TransferJobItem,
)


def mock_result(**method_returns) -> MagicMock:
    """A plain (non-Async) mock standing in for a SQLAlchemy ``Result``.

    ``AsyncMock().execute.return_value`` recursively defaults to another
    ``AsyncMock``, so sync ``Result`` methods like ``.all()``/``.first()``/
    ``.one_or_none()`` would otherwise silently return coroutines instead of
    configured values. Assign this to ``db.execute.return_value`` instead.
    """
    result = MagicMock()
    for method, value in method_returns.items():
        getattr(result, method).return_value = value
    return result


def mock_db() -> AsyncMock:
    """An AsyncSession-shaped mock: ``.execute``/``.flush`` are async (real
    SQLAlchemy behavior), ``.add`` is sync (real ``AsyncSession.add`` is NOT
    a coroutine function, unlike what a bare ``AsyncMock()`` would default
    ``.add`` to).
    """
    db = AsyncMock()
    db.add = MagicMock()
    return db


def make_session(**overrides) -> Session:
    defaults = dict(
        pysessid='hashed-pysessid',
        user_id='user-1',
        first_name='Nombre',
        last_name='Apellido',
        branch_id=999,
        role_id=1,
        ip_address='127.0.0.1',
        user_agent='pytest',
        created_at=utcnow(),
        expires_at=utcnow(),
        data={},
    )
    defaults.update(overrides)
    return Session(**defaults)


def make_branch_row(**overrides) -> SimpleNamespace:
    defaults = dict(id=1, name='Sucursal Uno', acronym='SU1')
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def make_inventory_row(**overrides) -> SimpleNamespace:
    defaults = dict(
        barcode='BC001',
        description='Anillo de oro',
        weight=5.0,
        retail_price=100.0,
        cost=50.0,
        observations=None,
        pawn_no='EMP-1',
        stone_weight=None,
        brand=None,
        model=None,
        series=None,
        carat_rating='14K',
        pawn_type='oro',
        branch='MASMEDAN Sucursal Uno',
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def make_transfer_job(**overrides) -> TransferJob:
    defaults = dict(
        job_id=str(uuid4()),
        owner_id='user-1',
        status=JobStatus.Pending,
        result=None,
        pushed_at=utcnow(),
        shifted_at=None,
        completed_at=None,
        tries=0,
        items=[],
        errors=[],
    )
    defaults.update(overrides)
    return TransferJob(**defaults)


def make_job_item(**overrides) -> TransferJobItem:
    defaults = dict(
        item_id=str(uuid4()),
        job_id=str(uuid4()),
        row_id='BC001',
        result=ItemResult.Pending,
    )
    defaults.update(overrides)
    return TransferJobItem(**defaults)


def make_job_error(**overrides) -> TransferJobError:
    defaults = dict(
        error_id=str(uuid4()),
        item_id=None,
        job_id=str(uuid4()),
        description=None,
        message='Ocurrió un error',
        occurred_at=utcnow(),
    )
    defaults.update(overrides)
    return TransferJobError(**defaults)


def _external_info(**overrides) -> dict:
    defaults = {
        'idPersona': '1', 'tipoDocumento': None, 'nroDocumento': None,
        'nombre': 'Nombre', 'apellido': 'Apellido', 'grupo': None,
        'sucursal': None, 'nroEmpleado': None, 'usuario': 'usuario1',
        'email': None, 'estado': None, 'eliminado': None,
        'idPerfil': '1', 'nombrePerfil': None, 'idSucursal': '999',
        'siglas': None, 'id': None, 'ordenamiento': None,
        'razonSocial': None, 'nombreComercial': None, 'rfc': None,
        'direccion': None, 'ciudad': None, 'municipio': None,
        'telefono': None, 'migrada': None, 'activa': None,
        'estadoSuc': None, 'visible': None, 'ElConix_Companie': None,
        'ElConix_CentroCosto': None, 'grupoSuc': None, 'doc_jefe_unidad': None,
    }
    defaults.update(overrides)
    return defaults


def _external_login(**overrides) -> dict:
    defaults = {
        'idLogin': '12345', 'idFake': None, 'idOriginal': None,
        'idGeneral': None, 'tipoLogin': None, 'usuario': 'usuario1',
        'clave': None, 'clave64': None, 'cambioClave': None,
        'primeraVez': None, 'verificado': None, 'estado': None,
        'created_at': None, 'updated_at': None, 'idPerfil': '1',
        'estadoper': None,
    }
    defaults.update(overrides)
    return defaults


def make_external_auth(
    continuar: int = 1,
    mensaje: str = 'OK',
    datos: dict | str | None = None,
    info_overrides: dict | None = None,
    login_overrides: dict | None = None,
) -> dict:
    if datos is not None:
        return {'continuar': continuar, 'mensaje': mensaje, 'datos': datos}
    return {
        'continuar': continuar,
        'mensaje': mensaje,
        'datos': {
            'ip': '127.0.0.1',
            'info': _external_info(**(info_overrides or {})),
            'login': _external_login(**(login_overrides or {})),
        },
    }
