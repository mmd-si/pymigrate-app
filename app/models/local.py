from collections import Counter
from datetime import datetime, timezone
from enum import StrEnum
from uuid import uuid4
from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_method
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.utils import utcnow
from app.models.base import LocalBase


class ItemResult(StrEnum):
    Pending = 'pendiente'
    Success = 'éxito'
    Failure = 'fracaso'


class JobResult(StrEnum):
    Success = 'éxito'
    Failure = 'fracaso'


class JobStatus(StrEnum):
    Pending = 'pendiente'
    Processing = 'en proceso'
    Completed = 'completado'


class ProductCategoryMap(LocalBase):
    __tablename__ = 'odoo_product_category_map'

    id: Mapped[int] = mapped_column(Integer, default=lambda: str(uuid4()), primary_key=True)
    category: Mapped[str] = mapped_column(String)
    kilataje: Mapped[str | None] = mapped_column(String, default=None)
    palabra_clave: Mapped[str] = mapped_column(String)
    categoria_odoo: Mapped[str] = mapped_column(String)


class Session(LocalBase):
    __tablename__ = 'sessions'
    __table_args__ = (Index('idx_uid_ip_ua', 'user_id', 'ip_address', 'user_agent'),)

    pysessid: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str | None] = mapped_column(String)
    first_name: Mapped[str | None] = mapped_column(String)
    last_name: Mapped[str | None] = mapped_column(String)
    branch_id: Mapped[int] = mapped_column(Integer)
    role_id: Mapped[int] = mapped_column(Integer)
    ip_address: Mapped[str] = mapped_column(String(45))
    user_agent: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: utcnow())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    data: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))

    @hybrid_method
    def is_branch_master(self) -> bool:
        return self.branch_id == 999 


class TransferJob(LocalBase):
    __tablename__ = 'transfer_jobs'

    __table_args__ = (
        Index(
            'idx_transfer_job_st_res_tries_pat',
            'status',
            'result',
            'tries',
            'pushed_at',
        ),
    )

    job_id: Mapped[str] = mapped_column(String, default=lambda: str(uuid4()), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String, default='')
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus, name='job_status'), default=JobStatus.Pending)
    result: Mapped[JobResult | None] = mapped_column(Enum(JobResult, name='job_result'))
    pushed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc))
    shifted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tries: Mapped[int] = mapped_column(Integer, default=0)

    errors: Mapped[list['TransferJobError']] = relationship(back_populates='job', lazy='raise')
    items: Mapped[list['TransferJobItem']] = relationship(back_populates='job', lazy='raise')

    @property
    def recount(self) -> dict[ItemResult, int]:
        counts = Counter(i.result for i in self.items)
        return {r: counts.get(r, 0) for r in ItemResult}


class TransferJobError(LocalBase):
    __tablename__ = 'transfer_job_errors'
    __table_args__ = (
        Index('idx_transfer_job_errors_jid_oat', 'job_id', 'occurred_at'),
    )
    error_id: Mapped[str] = mapped_column(
        String, default=lambda: str(uuid4()), primary_key=True
    )
    item_id: Mapped[str | None] = mapped_column(String, ForeignKey('transfer_job_items.item_id'))
    job_id: Mapped[str] = mapped_column(String, ForeignKey('transfer_jobs.job_id'))
    description: Mapped[str | None] = mapped_column(String)
    message: Mapped[str] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc))

    job: Mapped['TransferJob'] = relationship(back_populates='errors', lazy='raise')
    item: Mapped['TransferJobItem | None'] = relationship(back_populates='errors', lazy='raise')



class TransferJobItem(LocalBase):
    __tablename__ = 'transfer_job_items'

    __table_args__ = (Index('idx_transfer_job_item_jid_res', 'job_id', 'result'),)

    item_id: Mapped[str] = mapped_column(String, default=lambda: str(uuid4()), primary_key=True)
    job_id: Mapped[str] = mapped_column(String, ForeignKey('transfer_jobs.job_id'))
    row_id: Mapped[str] = mapped_column(String)
    result: Mapped[ItemResult] = mapped_column(
        Enum(ItemResult, name='item_result'),
        default=ItemResult.Pending
    )

    job: Mapped['TransferJob'] = relationship(back_populates='items', lazy='raise')
    errors: Mapped[list['TransferJobError']] = relationship(back_populates='item', lazy='raise')
