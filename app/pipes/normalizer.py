"""Turn a raw ERP inventory row into a clean ``JoinedItem``.

Ported from ``pymigrate/migrate-worker/app/pipes/normalizer.py``. The input is a
SQLAlchemy ``Row`` whose labels come from ``app.services.inventory._stmt()``.
"""

import logging

from sqlalchemy import Row

from app.schemas.odoo import JoinedItem

logger = logging.getLogger(__name__)


def noneif_na(text: str | None) -> str | None:
    if not text or text.strip().upper() == 'N/A':
        return None
    return text.strip()


def trimstr(text) -> str:
    if text is None:
        return ''
    return ' '.join(str(text).split())


def branch_title(branch: str | None) -> str:
    return (branch or '').replace('MASMEDAN', '').title()


class Normalizer:
    @staticmethod
    def normalize(item: Row) -> JoinedItem:
        try:
            return JoinedItem(
                barcode=(item.barcode or '').strip() or None,
                description=trimstr(item.description) or None,
                weight=float(item.weight) if item.weight is not None else None,
                retail_price=(
                    float(item.retail_price) if item.retail_price is not None else None
                ),
                cost=float(item.cost) if item.cost is not None else None,
                observations=trimstr(item.observations) or None,
                pawn_no=(item.pawn_no or '').strip() or None,
                stone_weight=(
                    float(item.stone_weight) if item.stone_weight is not None else None
                ),
                brand=noneif_na(trimstr(item.brand)),
                model=noneif_na(trimstr(item.model)),
                series=noneif_na(trimstr(item.series)),
                carat_rating=trimstr(item.carat_rating).upper() or None,
                pawn_type=trimstr(item.pawn_type) or None,
                branch=trimstr(branch_title(item.branch)) or None,
            )
        except Exception:
            logger.exception('failed to normalize inventory row')
            raise
