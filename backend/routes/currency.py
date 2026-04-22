from fastapi import APIRouter

from backend.currency import get_latest_rates

router = APIRouter(prefix="/currency", tags=["currency"])


@router.get("/rates")
def rates():
    return get_latest_rates()
