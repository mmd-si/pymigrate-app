from app.core.resolvers import procedural_resolver
from sqlalchemy import Row
from datetime import datetime
from pydantic import BaseModel, Field, computed_field
from app.models.local import ItemResult, JobStatus, Session, TransferJob, TransferJobError, TransferJobItem
from app.models.remote import Branch


class SimpleSession(BaseModel):
    user_id: str
    first_name: str | None
    last_name: str | None
    branch_id: int
    role_id: int
    ip_address: str
    user_agent: str
    data: dict

    @classmethod
    def from_session(cls, session: Session) -> 'SimpleSession':
        return cls(
            user_id=session.user_id,
            first_name=session.first_name,
            last_name=session.last_name,
            branch_id=session.branch_id,
            role_id=session.role_id,
            ip_address=session.ip_address,
            user_agent=session.user_agent,
            data=session.data
        )

class SimpleBranch(BaseModel):
    id: int
    name: str
    acronym: str | None

    @classmethod
    def from_branch(cls, branch: Branch) -> 'SimpleBranch':
        return SimpleBranch(id=branch.id, name=branch.nombreComercial, acronym=branch.siglas)

    @classmethod
    def from_row(cls, row: Row) -> 'SimpleBranch':
        return SimpleBranch(id=row.id, name=row.name, acronym=row.acronym)


class DetailedError(BaseModel):
    error_id: str
    job_id: str
    item_id: str | None
    description: str | None
    message: str
    occurred_at: datetime

    @classmethod
    def from_error(cls, error: TransferJobError) -> 'DetailedError':
        return DetailedError(
            error_id=error.error_id,
            job_id=error.job_id,
            item_id=error.item_id,
            description=error.description,
            message=error.message,
            occurred_at=error.occurred_at,
        )


class DetailedJobItem(BaseModel):
    item_id: str
    barcode: str
    item_name: str
    category: str
    result: ItemResult

    @classmethod
    def from_item(cls, item: TransferJobItem, product: InventoryDetails) -> 'DetailedJobItem':
        return DetailedJobItem(
            item_id=item.item_id,
            barcode=product.barcode,
            item_name=product.name,
            category=product.product_category,
            result=item.result,
        )


class InventoryDetails(BaseModel):
    internal_ref: str | None
    barcode: str | None
    description: str | None
    uom: str | None
    purchase_uom: str | None
    weight: float | None
    carat_rating: str | None
    can_be_sold: bool | None
    can_be_bought: bool | None
    product_type: str | None
    provider_tax: str | None
    customer_tax: str | None
    tags: str | None
    retail_price: float | None
    cost: float | None
    observations: str | None
    pawn_no: str | None
    pawn_type: str | None
    stone_weight: float | None
    brand: str | None
    model: str | None
    series: str | None
    raw_branch: str | None = Field(exclude=True)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def name(self) -> str | None:
        description = self.description
        carat_rating = self.carat_rating
        weight = self.weight
        pawn_type = self.pawn_type
        observations = self.observations
        barcode = self.barcode

        main = ' '.join(
            w
            for w in [
                (description.strip().title() if description else None),
                (carat_rating.strip() if carat_rating else None),
                (f'{weight}grs.' if weight and weight > 0 else None),
            ]
            if w
        )

        suffix = '-'.join(
            w.strip() for w in [pawn_type, observations, barcode] if w
        ).lower()

        result = ' '.join(w for w in [main, suffix] if w)
        return result or None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def product_category(self) -> str:
        return procedural_resolver(self)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def branch(self) -> str:
        raw_branch = self.raw_branch
        return '' if not raw_branch else ' '.join(raw_branch.replace('MASMEDAN', '').split())

    @classmethod
    def from_row(cls, row: Row) -> 'InventoryDetails':
        return InventoryDetails(
            internal_ref=row.barcode,
            barcode=row.barcode,
            description=row.description,
            uom='Unidades',
            purchase_uom='Unidades',
            weight=row.weight,
            carat_rating=row.carat_rating,
            can_be_sold=True,
            can_be_bought=False,
            product_type='Producto almacenable',
            provider_tax='ITBMS',
            customer_tax='ITBMS',
            tags='Lógica de etiquetas',
            retail_price=row.retail_price,
            cost=row.cost,
            observations=row.observations,
            pawn_no=row.pawn_no,
            pawn_type=row.pawn_type,
            stone_weight=row.stone_weight,
            brand=row.brand,
            model=row.model,
            series=row.series,
            raw_branch=row.branch,
        )


class DetailedJob(BaseModel):
    job_id: str
    status: JobStatus
    pushed_at: datetime
    shifted_at: datetime | None
    completed_at: datetime | None
    recount: dict[ItemResult, int]
    items: list[DetailedJobItem]
    errors: list[DetailedError]

    @classmethod
    def from_populated(cls, job: TransferJob, inventory: dict[str, InventoryDetails]) -> 'DetailedJob':
        return DetailedJob(
            job_id=job.job_id,
            status=job.status,
            pushed_at=job.pushed_at,
            shifted_at=job.shifted_at,
            completed_at=job.completed_at,
            recount=job.recount,
            items=[
                DetailedJobItem.from_item(item, inventory[item.row_id])
                for item in job.items
                if item.row_id in inventory
            ],
            errors=[DetailedError.from_error(e) for e in job.errors],
        )

class ErrorSummary(BaseModel):
    description: str | None
    message: str
    occurred_at: datetime

    @classmethod
    def from_model(cls, error: TransferJobError) -> ErrorSummary:
        return ErrorSummary(
            description=error.description, 
            message=error.message, 
            occurred_at=error.occurred_at
        )


class JobSummary(BaseModel):
    job_id: str
    status: JobStatus
    pushed_at: datetime
    recount: dict[ItemResult, int]
    latest_error: ErrorSummary | None

    @classmethod
    def from_populated(cls, job: TransferJob) -> JobSummary:
        error = sorted(job.errors, key=lambda e: e.occurred_at, reverse=True)[0] if job.errors else None
        return cls(
            job_id = job.job_id,
            status = job.status,
            pushed_at = job.pushed_at,
            recount = job.recount,
            latest_error = ErrorSummary.from_model(error) if error else None
        )