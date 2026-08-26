from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.models.local import ItemResult, JobStatus
from app.schemas.response import DetailedError, DetailedJob, DetailedJobItem
from app.services import report


def _detailed_job(**overrides) -> DetailedJob:
    defaults = dict(
        job_id='job-1',
        status=JobStatus.Completed,
        pushed_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        shifted_at=None,
        completed_at=None,
        recount={ItemResult.Pending: 1, ItemResult.Success: 2, ItemResult.Failure: 0},
        items=[DetailedJobItem(
            item_id='i1', barcode='BC001', item_name='Anillo', category='Oro',
            result=ItemResult.Success,
        )],
        errors=[DetailedError(
            error_id='e1', job_id='job-1', item_id=None, description=None,
            message='mensaje de error', occurred_at=datetime(2026, 1, 1, 13, 0, 0, tzinfo=timezone.utc),
        )],
    )
    defaults.update(overrides)
    return DetailedJob(**defaults)


class _FakePlaywrightContextManager:
    def __init__(self, pw):
        self._pw = pw

    async def __aenter__(self):
        return self._pw

    async def __aexit__(self, *args):
        return False


def test_format_datetime_returns_none_for_none():
    assert report._format_datetime(None) is None


def test_format_datetime_converts_from_utc_to_est():
    # America/Panama is a fixed UTC-5 offset (no DST): 05:00 UTC == 00:00 EST.
    utc_dt = datetime(2026, 6, 15, 5, 0, 0, tzinfo=timezone.utc)
    result = report._format_datetime(utc_dt)
    assert result is not None
    assert '12:00:00 AM' in result
    assert '05:00:00' not in result


async def test_create_transfer_report_renders_template_with_expected_context(monkeypatch):
    job = _detailed_job()
    mock_env = MagicMock()
    mock_env.get_template.return_value.render.return_value = '<html>report</html>'
    monkeypatch.setattr(report, 'env', mock_env)
    monkeypatch.setattr(report, 'locale', MagicMock())

    html = await report.create_transfer_report(job)

    assert html == '<html>report</html>'
    mock_env.get_template.assert_called_once_with('transfer.html')
    kwargs = mock_env.get_template.return_value.render.call_args.kwargs
    assert kwargs['job_id'] == 'job-1'
    assert kwargs['recount'] == {'pending': 1, 'success': 2, 'failure': 0}
    assert kwargs['items'] == [{
        'barcode': 'BC001', 'description': 'Anillo', 'category': 'Oro', 'result': ItemResult.Success,
    }]
    assert kwargs['errors'][0]['message'] == 'mensaje de error'


async def test_html_to_pdf_drives_playwright_and_returns_bytes(monkeypatch):
    page = AsyncMock()
    page.pdf.return_value = b'%PDF-bytes'
    browser = AsyncMock()
    browser.new_page.return_value = page
    chromium = AsyncMock()
    chromium.launch.return_value = browser
    pw = SimpleNamespace(chromium=chromium)

    monkeypatch.setattr(report, 'async_playwright', lambda: _FakePlaywrightContextManager(pw))

    result = await report._html_to_pdf('<html></html>')

    assert result == b'%PDF-bytes'
    chromium.launch.assert_awaited_once()
    browser.new_page.assert_awaited_once()
    page.set_content.assert_awaited_once_with('<html></html>', wait_until='networkidle')
    page.pdf.assert_awaited_once()
    browser.close.assert_awaited_once()


async def test_transfer_pdf_composes_html_render_and_pdf_export(monkeypatch):
    job = _detailed_job()
    monkeypatch.setattr(report, 'create_transfer_report', AsyncMock(return_value='<html>x</html>'))
    monkeypatch.setattr(report, '_html_to_pdf', AsyncMock(return_value=b'PDFBYTES'))

    result = await report.transfer_pdf(job)

    assert result == b'PDFBYTES'
    report._html_to_pdf.assert_awaited_once_with('<html>x</html>')
