from fastapi import APIRouter

from app.api.v1 import auth, branch, inventory, transfer

router = APIRouter(prefix='/v1')

router.include_router(auth.router)
router.include_router(branch.router)
router.include_router(transfer.router)