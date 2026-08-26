import locale
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from playwright.async_api import async_playwright
from app.core.utils import EST
from app.models.local import ItemResult
from app.schemas.response import DetailedJob

template_path = Path(__file__).resolve().parent.parent / 'templates'
env = Environment(loader=FileSystemLoader(template_path))

DATE_FORMAT = '%d de %B de %Y a las %I:%M:%S %p'


async def _html_to_pdf(html: str) -> bytes:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html, wait_until='networkidle')
        pdf = await page.pdf(
            format='A4',
            print_background=True,
            margin={
                'top': '10mm',
                'bottom': '10mm',
                'left': '10mm',
                'right': '10mm'
            }
        )
        await browser.close()
        return pdf


def _format_datetime(value: datetime | None) -> str | None:
    return value.astimezone(EST).strftime(DATE_FORMAT) if value else None


async def create_transfer_report(job: DetailedJob) -> str:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
    template = env.get_template('transfer.html')
    return template.render(
        base=template_path.as_uri(),
        job_id=job.job_id,
        pushed_at=_format_datetime(job.pushed_at),
        shifted_at=_format_datetime(job.shifted_at),
        completed_at=_format_datetime(job.completed_at),
        recount={
            'pending': job.recount[ItemResult.Pending],
            'success': job.recount[ItemResult.Success],
            'failure': job.recount[ItemResult.Failure],
        },
        items=[
            {
                'barcode': item.barcode,
                'description': item.item_name,
                'category': item.category,
                'result': item.result,
            }
            for item in job.items
        ],
        errors=[
            {
                'occurred_at': _format_datetime(error.occurred_at),
                'description': error.description,
                'message': error.message,
            }
            for error in job.errors
        ],
    )


async def transfer_pdf(job: DetailedJob) -> bytes:
    html = await create_transfer_report(job)
    return await _html_to_pdf(html)
