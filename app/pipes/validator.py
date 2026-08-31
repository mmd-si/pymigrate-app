"""Validate a ``JoinedItem`` before it is mapped to Odoo.

Ported from ``pymigrate/migrate-worker/app/pipes/validator.py``.
"""

import logging

from app.pipes.errors import ValidationError
from app.schemas.odoo import JoinedItem

logger = logging.getLogger(__name__)


class Validator:
    @staticmethod
    def validate(item: JoinedItem) -> JoinedItem:
        errors: list[str] = []

        if item.barcode is None:
            errors.append('El código de barra no puede estar vacío.')
        if item.weight is not None and item.weight < 0.0:
            errors.append('El peso del objeto no puede ser negativo.')
        if item.retail_price is not None and item.retail_price < 0.0:
            errors.append('El precio de venta del objeto no puede ser negativo.')
        if item.cost is not None and item.cost < 0.0:
            errors.append('El costo del objeto no puede ser negativo.')
        if item.stone_weight is not None and item.stone_weight < 0.0:
            errors.append('El peso de las piedras del objeto no puede ser negativo.')

        if errors:
            message = '\n'.join(errors)
            logger.warning('validation failed: %s', message)
            raise ValidationError(message)

        return item
