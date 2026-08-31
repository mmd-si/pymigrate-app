from unittest.mock import AsyncMock, patch

from app.jobs import transfer as drain
from app.models.local import ItemResult, JobResult, JobStatus
from app.schemas.odoo import (
    M2MOp,
    OdooProductType,
    ProductTemplateSchema,
)
from tests.support.builders import (
    make_job_item,
    make_odoo_context,
    make_source_row,
    make_transfer_job,
    mock_db,
)


def _template() -> ProductTemplateSchema:
    return ProductTemplateSchema(
        default_code='BC001', barcode='BC001', name='Anillo', uom_id=1, uom_po_id=1,
        weight=5.0, sale_ok=True, purchase_ok=False, available_in_pos=True,
        pos_categ_ids=[(M2MOp.Replace, 0, [1])], type=OdooProductType.Goods,
        supplier_taxes_id=[(M2MOp.Replace, 0, [2])], taxes_id=[(M2MOp.Replace, 0, [3])],
        product_tag_ids=[(M2MOp.Replace, 0, [4])], list_price=100.0, standard_price=50.0,
        description=None, warehouse_id=11, categ_id=22,
    )


def _odoo_ctx() -> object:
    ctx = make_odoo_context()
    # insert() is variadic and batches: N rows in -> N ids out.
    ctx.product_template.insert.side_effect = lambda *rows: [101 + i for i in range(len(rows))]
    ctx.product_product.get_product_ids.side_effect = lambda tids: {t: 900 + t for t in tids}
    ctx.product_product.get_product_id.return_value = 9  # per-row fallback
    ctx.stock_picking.build_for_product.side_effect = lambda *a, **k: object()
    ctx.stock_picking.insert.side_effect = lambda *pks: list(range(len(pks)))
    return ctx


def _patches(jobs, rows, ctx):
    return (
        patch.object(drain.jobrunner, 'claim_pending', AsyncMock(return_value=jobs)),
        patch.object(drain.inventory, 'source_rows', AsyncMock(return_value=rows)),
        patch.object(drain.OdooContext, 'create', AsyncMock(return_value=ctx)),
        patch.object(drain.Mapper, 'map', AsyncMock(return_value=_template())),
    )


async def test_drain_happy_path_completes_job_and_items():
    lcl, rmt = mock_db(), mock_db()
    items = [make_job_item(row_id='BC001'), make_job_item(row_id='BC002')]
    job = make_transfer_job(status=JobStatus.Processing, items=items)
    rows = [make_source_row(barcode='BC001'), make_source_row(barcode='BC002')]
    ctx = _odoo_ctx()

    p1, p2, p3, p4 = _patches([job], rows, ctx)
    with p1, p2, p3, p4:
        await drain.drain_once(lcl, rmt)

    assert job.status is JobStatus.Completed
    assert job.result is JobResult.Success
    assert all(i.result is ItemResult.Success for i in items)
    # both rows go to Odoo in a single batched call each, not one call per row
    assert ctx.product_template.insert.await_count == 1
    assert ctx.product_product.get_product_ids.await_count == 1
    assert ctx.stock_picking.insert.await_count == 1
    assert len(ctx.stock_picking.insert.await_args.args) == 2
    lcl.commit.assert_awaited()


async def test_drain_no_source_rows_fails_job():
    lcl, rmt = mock_db(), mock_db()
    job = make_transfer_job(status=JobStatus.Processing, items=[make_job_item(row_id='BC001')])
    ctx = _odoo_ctx()

    p1, p2, p3, p4 = _patches([job], [], ctx)
    with p1, p2, p3, p4:
        await drain.drain_once(lcl, rmt)

    assert job.status is JobStatus.Completed
    assert job.result is JobResult.Failure
    lcl.add.assert_called()  # an error row was recorded


async def test_drain_validation_failure_fails_item_but_not_job():
    lcl, rmt = mock_db(), mock_db()
    items = [make_job_item(row_id='OK'), make_job_item(row_id='BAD')]
    job = make_transfer_job(status=JobStatus.Processing, items=items)
    rows = [
        make_source_row(barcode='OK'),
        make_source_row(barcode='BAD', weight=-3.0),  # fails Validator
    ]
    ctx = _odoo_ctx()

    p1, p2, p3, p4 = _patches([job], rows, ctx)
    with p1, p2, p3, p4:
        await drain.drain_once(lcl, rmt)

    by_row = {i.row_id: i for i in items}
    assert by_row['OK'].result is ItemResult.Success
    assert by_row['BAD'].result is ItemResult.Failure
    assert job.result is JobResult.Success  # job still completes
    lcl.add.assert_called()  # error row for BAD


async def test_drain_returns_early_when_no_jobs():
    lcl, rmt = mock_db(), mock_db()
    with (
        patch.object(drain.jobrunner, 'claim_pending', AsyncMock(return_value=[])),
        patch.object(drain.OdooContext, 'create', AsyncMock()) as create,
    ):
        await drain.drain_once(lcl, rmt)
    create.assert_not_awaited()
