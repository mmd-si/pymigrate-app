"""The transfer-job consumer, folded in from ``pymigrate/migrate-worker``.

``run_drain`` is the entrypoint used both by the APScheduler interval job
(``app.core.scheduler``) and by the ``BackgroundTask`` kicked from
``POST /api/v1/transfers``. It claims a batch of pending jobs, pulls their source
rows from the legacy ERP, runs each through the normalize -> validate -> map
pipeline, then pushes the whole job into Odoo in batched round trips -- one
``product.template`` multi-create, one ``product.product`` lookup, one
``stock.picking`` multi-create -- and only drops to per-row calls when a batch
call fails, so one bad row never sinks its siblings. Per-item results and error
rows are written back throughout.
"""

import logging
from typing import Awaitable, Callable

from sqlalchemy import Row
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.db import LocalSession, RemoteSession
from app.config.settings import Settings, get_settings
from app.core.retry import retry
from app.models.local import ItemResult, JobResult, TransferJob, TransferJobItem
from app.odoo import OdooContext
from app.pipes.errors import PipelineError, ValidationError
from app.pipes.mapper import Mapper
from app.pipes.normalizer import Normalizer
from app.pipes.pipe import Pipe
from app.pipes.validator import Validator
from app.schemas.odoo import ProductTemplateSchema
from app.services import inventory, jobrunner

logger = logging.getLogger(__name__)

_PRODUCT_ERROR = 'Error al insertar el producto en Odoo'
_PICKING_ERROR = 'Error al crear movimiento de inventario en Odoo'


async def run_drain() -> None:
    """Own a fresh pair of sessions, run one drain cycle, and never raise -- a
    failure here must not kill the scheduler or a request's background task."""
    try:
        async with LocalSession() as lcl, RemoteSession() as rmt:
            await drain_once(lcl, rmt)
    except Exception:
        logger.exception('transfer drain cycle failed')


async def drain_once(lcl: AsyncSession, rmt: AsyncSession) -> None:
    settings = get_settings()

    jobs = await jobrunner.claim_pending(
        lcl, settings.transfer_batch_limit, settings.transfer_max_tries
    )
    # Commit the claim immediately so a crash mid-cycle leaves the jobs in
    # Processing (durable progress) rather than silently rolled back.
    await lcl.commit()
    if not jobs:
        return

    logger.info('claimed %d transfer job(s)', len(jobs))
    odoo = await OdooContext.create(settings)

    for job in jobs:
        try:
            await _process_job(lcl, rmt, odoo, job, settings)
            await lcl.commit()
        except Exception:
            logger.exception('transfer job %s failed unexpectedly', job.job_id)
            await lcl.rollback()


async def _process_job(
    lcl: AsyncSession,
    rmt: AsyncSession,
    odoo: OdooContext,
    job: TransferJob,
    settings: Settings,
) -> None:
    items = jobrunner.outstanding_items(job)
    barcodes = [i.row_id for i in items]

    rows = await retry(
        lambda: inventory.source_rows(rmt, barcodes), tries=settings.transfer_max_tries
    )
    if not rows:
        await jobrunner.record_error(
            lcl,
            job.job_id,
            'No se encontraron productos con los códigos de barra enviados.',
            description='Error extrayendo productos de la base de datos remota',
        )
        await jobrunner.finish_job(lcl, job, JobResult.Failure)
        return

    by_barcode: dict[str, Row] = {r.barcode: r for r in rows}
    tries = settings.transfer_max_tries

    # Pass 1 -- normalize -> validate -> map every item. Failures are recorded and
    # dropped here so later passes only ever see good rows. Sequential on purpose:
    # Mapper.map warms a shared OdooCache, and concurrent misses would
    # double-create master data (tags, category tree).
    mapped: list[tuple[TransferJobItem, ProductTemplateSchema]] = []
    for item in items:
        row = by_barcode.get(item.row_id)
        if row is None:
            await jobrunner.record_error(
                lcl,
                job.job_id,
                f'No se encontró el producto con código {item.row_id}.',
                description='Producto ausente en la base de datos remota',
                item_id=item.item_id,
            )
            await jobrunner.mark_item(lcl, item, ItemResult.Failure)
            continue
        schema = await _map_item(lcl, odoo, job, item, row, settings)
        if schema is not None:
            mapped.append((item, schema))

    # Pass 2 -- one product.template multi-create for the whole job.
    templated = await _batched(
        mapped,
        [schema for _, schema in mapped],
        lambda payloads: odoo.product_template.insert(*payloads),
        lambda payload: _first(odoo.product_template.insert(payload)),
        lcl=lcl,
        job=job,
        description=_PRODUCT_ERROR,
        tries=tries,
    )

    # Pass 3 -- one product.product lookup mapping template id -> variant id.
    resolved = await _resolve_variants(lcl, odoo, job, templated, tries)

    # Pass 4 -- build every picking, then one stock.picking multi-create.
    built: list[tuple[TransferJobItem, object]] = []
    for item, schema, product_id in resolved:
        try:
            picking = await odoo.stock_picking.build_for_product(
                odoo.stock_warehouse,
                odoo.stock_picking_type,
                job.job_id,
                product_id,
                schema,
            )
        except Exception as e:
            await jobrunner.record_error(
                lcl, job.job_id, str(e),
                description=_PICKING_ERROR, item_id=item.item_id,
            )
            await jobrunner.mark_item(lcl, item, ItemResult.Failure)
            continue
        built.append((item, picking))

    done = await _batched(
        built,
        [picking for _, picking in built],
        lambda payloads: odoo.stock_picking.insert(*payloads),
        lambda payload: _first(odoo.stock_picking.insert(payload)),
        lcl=lcl,
        job=job,
        description=_PICKING_ERROR,
        tries=tries,
    )
    for (item, _picking), _id in done:
        await jobrunner.mark_item(lcl, item, ItemResult.Success)

    # Unconditional, matching the worker: item rows carry their own failures; a
    # job-level Failure is only for the "no source rows at all" case above.
    await jobrunner.finish_job(lcl, job, JobResult.Success)


async def _map_item(
    lcl: AsyncSession,
    odoo: OdooContext,
    job: TransferJob,
    item: TransferJobItem,
    row: Row,
    settings: Settings,
) -> ProductTemplateSchema | None:
    """Run the CPU-bound normalize/validate stages and the async Mapper.map for
    one item. Records the error and returns ``None`` on any failure."""
    try:
        joined = (
            Pipe.of(row)
            .pipe(Normalizer.normalize)
            .pipe(Validator.validate)
            .peek()
        )
    except (PipelineError, ValidationError) as e:
        await jobrunner.record_error(
            lcl, job.job_id, str(e),
            description='Error en el pipeline de transformación',
            item_id=item.item_id,
        )
        await jobrunner.mark_item(lcl, item, ItemResult.Failure)
        return None
    except Exception as e:
        await jobrunner.record_error(
            lcl, job.job_id, str(e),
            description='Error desconocido en el pipeline de transformación',
            item_id=item.item_id,
        )
        await jobrunner.mark_item(lcl, item, ItemResult.Failure)
        return None

    try:
        return await retry(
            lambda: Mapper.map(odoo, joined, settings), tries=settings.transfer_max_tries
        )
    except Exception as e:
        await jobrunner.record_error(
            lcl, job.job_id, str(e),
            description=_PRODUCT_ERROR, item_id=item.item_id,
        )
        await jobrunner.mark_item(lcl, item, ItemResult.Failure)
        return None


async def _resolve_variants(
    lcl: AsyncSession,
    odoo: OdooContext,
    job: TransferJob,
    templated: list[tuple[tuple[TransferJobItem, ProductTemplateSchema], int]],
    tries: int,
) -> list[tuple[TransferJobItem, ProductTemplateSchema, int]]:
    """Turn ``((item, schema), template_id)`` pairs into ``(item, schema,
    variant_id)`` triples, resolving every variant in one ``search_read`` and
    dropping to a per-row lookup only for the ids the batch call missed."""
    if not templated:
        return []

    template_ids = [tid for _, tid in templated]
    try:
        variant_of = await retry(
            lambda: odoo.product_product.get_product_ids(template_ids), tries=tries
        )
    except Exception:
        logger.warning(
            'batch variant lookup failed for job %s; isolating rows',
            job.job_id, exc_info=True,
        )
        variant_of = {}

    out: list[tuple[TransferJobItem, ProductTemplateSchema, int]] = []
    for (item, schema), tid in templated:
        product_id = variant_of.get(tid)
        if product_id is None:
            try:
                product_id = await retry(
                    lambda t=tid: odoo.product_product.get_product_id(t), tries=tries
                )
            except Exception:
                product_id = None
        if product_id is None:
            await jobrunner.record_error(
                lcl, job.job_id,
                'No se encontró la variante del producto recién creado en Odoo.',
                description=_PRODUCT_ERROR, item_id=item.item_id,
            )
            await jobrunner.mark_item(lcl, item, ItemResult.Failure)
            continue
        out.append((item, schema, product_id))
    return out


async def _first[T](awaitable: Awaitable[list[T]]) -> T:
    return (await awaitable)[0]


async def _batched[T: tuple, P, R](
    entries: list[T],
    payloads: list[P],
    batch_call: Callable[[list[P]], Awaitable[list[R]]],
    single_call: Callable[[P], Awaitable[R]],
    *,
    lcl: AsyncSession,
    job: TransferJob,
    description: str,
    tries: int,
) -> list[tuple[T, R]]:
    """Issue ``batch_call`` once for every payload; if it raises or returns the
    wrong number of results, fall back to ``single_call`` per row and record
    ``description`` against the items that still fail. Each entry in ``entries``
    is a tuple whose first element is the ``TransferJobItem`` (for error
    attribution); the returned pairs keep those entries intact.
    """
    if not entries:
        return []
    try:
        results = await retry(lambda: batch_call(payloads), tries=tries)
        if len(results) == len(entries):
            return list(zip(entries, results))
        logger.warning(
            'batch call for job %s returned %d results for %d rows; isolating',
            job.job_id, len(results), len(entries),
        )
    except Exception:
        logger.warning(
            'batch call for job %s failed; isolating rows', job.job_id, exc_info=True
        )

    out: list[tuple[T, R]] = []
    for entry, payload in zip(entries, payloads):
        item: TransferJobItem = entry[0]
        try:
            out.append((entry, await retry(lambda p=payload: single_call(p), tries=tries)))
        except Exception as e:
            await jobrunner.record_error(
                lcl, job.job_id, str(e),
                description=description, item_id=item.item_id,
            )
            await jobrunner.mark_item(lcl, item, ItemResult.Failure)
    return out
