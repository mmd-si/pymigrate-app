"""Plain dataclasses that model the payloads sent to Odoo over XML-RPC, plus
the source-agnostic ``JoinedItem`` produced by the transformation pipeline.

Ported from ``pymigrate/migrate-worker/app/schema/*``. These are deliberately
*not* Pydantic models: ``serialize()`` mirrors Odoo's ``create`` argument shape
(``(6, 0, [ids])`` m2m triples, ``"%Y-%m-%d %H:%M:%S"`` datetimes) and Pydantic
would fight that.
"""

from abc import ABC
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, IntEnum, StrEnum


class M2MOp(IntEnum):
    """Odoo (command, id, values) many2many/one2many write op codes."""

    Create = 0
    Update = 1
    Delete = 2
    Unlink = 3
    Link = 4
    Clear = 5
    Replace = 6


class OdooProductType(StrEnum):
    Goods = 'consu'
    Services = 'service'
    Combination = 'combo'


class OdooPickingState(StrEnum):
    Draft = 'draft'
    Waiting = 'waiting'
    Confirmed = 'confirmed'
    Assigned = 'assigned'
    Done = 'done'
    Cancelled = 'cancel'


class OdooPriority(StrEnum):
    Normal = '0'
    Urgent = '1'


@dataclass
class JoinedItem:
    """The normalized, source-agnostic product record: output of ``Normalizer``,
    input to ``Validator`` and ``Mapper``.
    """

    barcode: str | None
    description: str | None
    weight: float | None
    retail_price: float | None
    cost: float | None
    observations: str | None
    pawn_no: str | None
    stone_weight: float | None
    brand: str | None
    model: str | None
    series: str | None
    carat_rating: str | None
    pawn_type: str | None
    branch: str | None


@dataclass
class OdooSerializable(ABC):
    def serialize(self) -> dict:
        def normalize(value):
            if isinstance(value, Enum):
                return value.value
            if isinstance(value, datetime):
                return value.strftime('%Y-%m-%d %H:%M:%S')
            if isinstance(value, OdooSerializable):
                return value.serialize()
            if isinstance(value, dict):
                return {k: normalize(v) for k, v in value.items()}
            if isinstance(value, (list, tuple)):
                return type(value)(normalize(v) for v in value)
            return value

        return {
            k: normalize(v)
            for k in self.__dataclass_fields__
            if (v := getattr(self, k)) is not None
        }


@dataclass
class ProductTemplateSchema(OdooSerializable):
    default_code: str
    barcode: str
    name: str
    uom_id: int
    uom_po_id: int
    weight: float | None
    sale_ok: bool
    purchase_ok: bool
    available_in_pos: bool
    pos_categ_ids: list[tuple[int, int, list[int]]]
    type: OdooProductType
    supplier_taxes_id: list[tuple[int, int, list[int]]]
    taxes_id: list[tuple[int, int, list[int]]]
    product_tag_ids: list[tuple[int, int, list[int]]]
    list_price: float | None
    standard_price: float | None
    description: str | None
    warehouse_id: int
    categ_id: int


@dataclass
class StockMoveSchema(OdooSerializable):
    name: str
    product_id: int
    product_uom_qty: float
    product_uom: int
    location_id: int
    location_dest_id: int


@dataclass
class StockPickingSchema(OdooSerializable):
    priority: OdooPriority
    picking_type_id: int
    location_id: int
    state: OdooPickingState
    location_dest_id: int
    scheduled_date: datetime
    origin: str
    move_ids: list[tuple[int, int, StockMoveSchema]]
    note: str
    partner_id: int | None = None
    batch_id: int | None = None
