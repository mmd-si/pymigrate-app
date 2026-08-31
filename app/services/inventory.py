from sqlalchemy import Row, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.remote import InventoryEntry as IE, Branch as Br, PawnType as PT, CaratRating as CR
from app.schemas.response import InventoryDetails
from app.services.branch import GRUPO_SI


def _conditions(branch_id: int | None = None, barcode: str | None = None):
    return [c for c in [
            IE.cantidad >= 1,
            Br.grupo == GRUPO_SI,
            IE.sucursalDestino >= 803,
            (IE.sucursalDestino == branch_id) if branch_id is not None else None,
            (IE.codigo == barcode) if barcode is not None else None,
        ] if c is not None]


def _stmt(branch_id: int | None = None, barcode: str | None = None):
    return (
        select(
            IE.codigo.label('barcode'),
            IE.descripcion.label('description'),
            IE.pesoDotacion.label('weight'),
            IE.precio.label('retail_price'),
            IE.costo.label('cost'),
            IE.observaciones.label('observations'),
            IE.idEmpeno.label('pawn_no'),
            IE.pesoPiedras.label('stone_weight'),
            IE.marca.label('brand'),
            IE.modelo.label('model'),
            IE.serie.label('series'),
            CR.nombreKilataje.label('carat_rating'),
            PT.nombreTipoEmpeno.label('pawn_type'),
            Br.nombreComercial.label('branch'),
        )
        .join(Br, IE.sucursalDestino == Br.id)
        .outerjoin(PT, IE.tipoDotacion == PT.idTipoEmpeno)
        .outerjoin(CR, IE.kilates == CR.Clave)
        .where(*_conditions(branch_id, barcode))
        .order_by(IE.id_entrada_inventario.desc())
    )


async def by_branch_and_barcode(db: AsyncSession, branch_id: int, barcode: str) -> InventoryDetails | None:
    row = (await db.execute(_stmt(branch_id, barcode))).first()
    if row is None:
        return None
    return InventoryDetails.from_row(row)


async def with_barcode_in(db: AsyncSession, barcodes: list[str]) -> list[InventoryDetails]:
    if not barcodes:
        return []
    stmt = _stmt().where(IE.codigo.in_(barcodes))
    result = await db.execute(stmt)
    return [InventoryDetails.from_row(row) for row in result]


async def group_by_barcodes(db: AsyncSession, barcodes: list[str]) -> dict[str, InventoryDetails]:
    if not barcodes:
        return {}
    stmt = _stmt().where(IE.codigo.in_(barcodes))
    result = await db.execute(stmt)
    return {row.barcode: InventoryDetails.from_row(row) for row in result}


async def source_rows(db: AsyncSession, barcodes: list[str]) -> list[Row]:
    """Raw ERP rows for the given barcodes, with the column labels the transfer
    pipeline's ``Normalizer`` expects. Unlike ``with_barcode_in`` this does not
    project into ``InventoryDetails``."""
    if not barcodes:
        return []
    result = await db.execute(_stmt().where(IE.codigo.in_(barcodes)))
    return list(result.all())


async def existing_only(db: AsyncSession, barcodes: list[str]) -> list[str]:
    stmt = (
        select(IE.codigo.label('barcode'))
        .join(Br, IE.sucursalDestino == Br.id)
        .where(*_conditions(), IE.codigo.in_(barcodes))
    )
    result = await db.execute(stmt)
    return [row.barcode for row in result]
