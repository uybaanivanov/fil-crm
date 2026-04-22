import datetime
import os
import time
import uuid
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field

from backend.auth import require_role
from backend.db import get_conn
from backend.parsers import UnsupportedSource

router = APIRouter(prefix="/apartments", tags=["apartments"])


class ApartmentIn(BaseModel):
    title: str = Field(min_length=1)
    address: str = Field(min_length=1)
    price_per_night: int = Field(gt=0)
    rooms: str | None = None
    area_m2: int | None = Field(default=None, gt=0)
    floor: str | None = None
    district: str | None = None
    callsign: str | None = None
    cover_url: str | None = None
    source: str | None = None
    source_url: str | None = None
    monthly_rent: int | None = Field(default=None, ge=0)
    monthly_utilities: int | None = Field(default=None, ge=0)
    entrance: str | None = None
    apt_number: str | None = None
    intercom_code: str | None = None
    safe_code: str | None = None
    utility_account: str | None = None
    price_weekday: int | None = Field(default=None, ge=0)
    price_weekend: int | None = Field(default=None, ge=0)


class ApartmentPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    address: str | None = Field(default=None, min_length=1)
    price_per_night: int | None = Field(default=None, gt=0)
    rooms: str | None = None
    area_m2: int | None = Field(default=None, gt=0)
    floor: str | None = None
    district: str | None = None
    callsign: str | None = None
    cover_url: str | None = None
    source: str | None = None
    source_url: str | None = None
    monthly_rent: int | None = Field(default=None, ge=0)
    monthly_utilities: int | None = Field(default=None, ge=0)
    entrance: str | None = None
    apt_number: str | None = None
    intercom_code: str | None = None
    safe_code: str | None = None
    utility_account: str | None = None
    price_weekday: int | None = Field(default=None, ge=0)
    price_weekend: int | None = Field(default=None, ge=0)


class CleaningDueIn(BaseModel):
    cleaning_due_at: datetime.datetime


SELECT_FIELDS = (
    "id, title, address, price_per_night, needs_cleaning, cleaning_due_at, "
    "cover_url, rooms, area_m2, floor, district, callsign, source, source_url, "
    "monthly_rent, monthly_utilities, "
    "entrance, apt_number, intercom_code, safe_code, utility_account, "
    "price_weekday, price_weekend, created_at"
)


def _row(conn, apt_id: int):
    return conn.execute(
        f"SELECT {SELECT_FIELDS} FROM apartments WHERE id = ?", (apt_id,)
    ).fetchone()


@router.get("")
def list_apartments(
    with_stats: int = Query(0),
    month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
    q: str | None = Query(None),
    check_in: str | None = Query(None),
    check_out: str | None = Query(None),
    _: dict = Depends(require_role("owner", "admin")),
):
    if check_in and check_out:
        next_select = (
            "(SELECT MIN(b.check_in) FROM bookings b"
            " WHERE b.apartment_id = a.id"
            "   AND b.status = 'active'"
            "   AND b.check_out > ? AND b.check_in < ?) AS next_booked_from"
        )
        next_params: list = [check_in, check_out]
    else:
        next_select = "NULL AS next_booked_from"
        next_params = []

    select_cols = ", ".join(f"a.{c}" for c in [
        "id", "title", "address", "price_per_night", "needs_cleaning", "cleaning_due_at",
        "cover_url", "rooms", "area_m2", "floor", "district", "callsign", "source", "source_url",
        "monthly_rent", "monthly_utilities",
        "entrance", "apt_number", "intercom_code", "safe_code", "utility_account",
        "price_weekday", "price_weekend", "created_at",
    ])

    sql = (
        f"SELECT {select_cols}, {next_select} FROM apartments a "
        "ORDER BY (next_booked_from IS NULL) DESC, a.id ASC"
    )
    full_params = next_params

    with get_conn() as conn:
        rows = conn.execute(sql, full_params).fetchall()
        apts = [dict(r) for r in rows]
        if q:
            q_low = q.lower()
            apts = [
                a for a in apts
                if q_low in (a.get("callsign") or "").lower()
                or q_low in (a.get("address") or "").lower()
            ]
        if not with_stats:
            return apts

        from datetime import date

        from backend.lib.stats import (
            aggregate_bookings_in_period,
            days_in_month,
            month_bounds,
        )

        month = month or date.today().strftime("%Y-%m")
        p_start, p_end = month_bounds(month)
        dim = days_in_month(month)
        today = date.today().isoformat()
        for a in apts:
            bookings = conn.execute(
                "SELECT check_in, check_out, total_price, status FROM bookings WHERE apartment_id = ?",
                (a["id"],),
            ).fetchall()
            bookings = [dict(b) for b in bookings]
            agg = aggregate_bookings_in_period(bookings, p_start, p_end)
            a["nights"] = agg["nights"]
            a["revenue"] = agg["revenue"]
            a["adr"] = agg["adr"]
            a["utilization"] = round(agg["nights"] / dim, 4) if dim else 0.0
            # Статус: если есть бронь где check_in<=today<check_out и status='active' — occupied;
            # иначе если needs_cleaning=1 — needs_cleaning; иначе free.
            is_occupied = any(
                b["status"] == "active"
                and b["check_in"] <= today < b["check_out"]
                for b in bookings
            )
            if is_occupied:
                a["status"] = "occupied"
            elif a["needs_cleaning"]:
                a["status"] = "needs_cleaning"
            else:
                a["status"] = "free"
    return apts


@router.get("/cleaning")
def list_apartments_needing_cleaning(
    _: dict = Depends(require_role("owner", "admin", "maid")),
):
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT {SELECT_FIELDS} FROM apartments "
            "WHERE needs_cleaning = 1 "
            "ORDER BY cleaning_due_at IS NULL, cleaning_due_at ASC, id"
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/{apt_id}")
def get_apartment(
    apt_id: int, _: dict = Depends(require_role("owner", "admin"))
):
    with get_conn() as conn:
        row = _row(conn, apt_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Квартира не найдена")
    return dict(row)


@router.get("/{apt_id}/stats")
def apartment_stats(
    apt_id: int,
    month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
    _: dict = Depends(require_role("owner", "admin")),
):
    from datetime import date

    from backend.lib.stats import (
        aggregate_bookings_in_period,
        days_in_month,
        month_bounds,
    )

    month = month or date.today().strftime("%Y-%m")
    p_start, p_end = month_bounds(month)
    dim = days_in_month(month)
    with get_conn() as conn:
        if _row(conn, apt_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Квартира не найдена")
        rows = conn.execute(
            "SELECT check_in, check_out, total_price, status FROM bookings WHERE apartment_id = ?",
            (apt_id,),
        ).fetchall()
    bookings = [dict(r) for r in rows]
    agg = aggregate_bookings_in_period(bookings, p_start, p_end)
    agg["utilization"] = round(agg["nights"] / dim, 4) if dim else 0.0
    return agg


@router.post("", status_code=status.HTTP_201_CREATED)
def create_apartment(
    payload: ApartmentIn, _: dict = Depends(require_role("owner"))
):
    import sqlite3

    fields = payload.model_dump()
    cols = ", ".join(fields.keys())
    placeholders = ", ".join("?" * len(fields))
    try:
        with get_conn() as conn:
            cur = conn.execute(
                f"INSERT INTO apartments ({cols}) VALUES ({placeholders})",
                list(fields.values()),
            )
            new_id = cur.lastrowid
            if payload.cover_url and payload.cover_url.startswith("/media/apartments/_pending/"):
                from_path = _media_root() / "apartments" / "_pending" / Path(payload.cover_url).name
                ext = from_path.suffix.lstrip(".")
                if from_path.exists() and ext in _ALLOWED_COVER_TYPES.values():
                    target_dir = _media_root() / "apartments" / str(new_id)
                    target_dir.mkdir(parents=True, exist_ok=True)
                    for old in target_dir.glob("cover.*"):
                        try:
                            old.unlink()
                        except OSError:
                            pass
                    target = target_dir / f"cover.{ext}"
                    from_path.rename(target)
                    new_url = f"/media/apartments/{new_id}/cover.{ext}"
                    conn.execute(
                        "UPDATE apartments SET cover_url = ? WHERE id = ?",
                        (new_url, new_id),
                    )
            row = _row(conn, new_id)
    except sqlite3.IntegrityError as e:
        msg = str(e)
        if "apartments_source_url_uniq" in msg or "apartments.source_url" in msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Квартира с такой ссылкой уже есть",
            )
        raise
    return dict(row)


class ParseUrlIn(BaseModel):
    url: str = Field(min_length=1)


async def _fetch_listing(url: str):
    """Резолв редиректа, старт MoreLogin, Playwright через CDP, парсер.
    Вынесено, чтобы тесты могли подменить через monkeypatch."""
    from urllib.parse import urlparse

    from playwright.async_api import async_playwright

    from backend import morelogin
    from backend.parsers import parse_html, resolve_final_url, resolve_source

    _ALLOWED = {
        "doska.ykt.ru", "www.doska.ykt.ru",
        "youla.ru", "www.youla.ru",
        "trk.mail.ru",
    }
    host = urlparse(url).netloc.lower()
    if host not in _ALLOWED:
        raise UnsupportedSource(f"unsupported host: {host}")

    final_url = resolve_final_url(url)
    resolve_source(final_url)

    session = await morelogin.start_profile()
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(session.cdp_url)
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()
        for other in list(ctx.pages):
            if other is not page:
                await other.close()
        await page.goto(final_url, wait_until="load", timeout=60000)
        html = await page.content()
        await page.close()
    return parse_html(html, final_url)


@router.post("/parse-url")
async def parse_url(
    payload: ParseUrlIn, _: dict = Depends(require_role("owner"))
):
    from backend.parsers import ParseError

    try:
        listing = await _fetch_listing(payload.url)
    except UnsupportedSource as e:
        raise HTTPException(status_code=422, detail=f"unsupported_source: {e}")
    except ParseError as e:
        raise HTTPException(status_code=422, detail=f"parse_failed: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"fetch_failed: {e}")
    if listing.cover_url:
        localized = _localize_cover(listing.cover_url)
        if localized:
            listing.cover_url = localized
    return listing.to_dict()


@router.patch("/{apt_id}")
def update_apartment(
    apt_id: int,
    payload: ApartmentPatch,
    _: dict = Depends(require_role("owner", "admin")),
):
    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Нет полей для обновления"
        )
    with get_conn() as conn:
        current = _row(conn, apt_id)
        if current is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Квартира не найдена"
            )
        merged_rent = fields.get("monthly_rent", current["monthly_rent"])
        if merged_rent is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="monthly_rent обязателен",
            )
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [apt_id]
        conn.execute(
            f"UPDATE apartments SET {set_clause} WHERE id = ?", values
        )
        row = _row(conn, apt_id)
    return dict(row)


@router.delete("/{apt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_apartment(apt_id: int, _: dict = Depends(require_role("owner", "admin"))):
    import sqlite3

    try:
        with get_conn() as conn:
            cur = conn.execute("DELETE FROM apartments WHERE id = ?", (apt_id,))
            if cur.rowcount == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Квартира не найдена"
                )
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Нельзя удалить квартиру с привязанными бронями",
        )
    return None


def _media_root() -> Path:
    return Path(os.environ.get("FIL_MEDIA_DIR") or (Path(__file__).resolve().parent.parent / "media"))


_ALLOWED_COVER_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
_MAX_COVER_SIZE = 5 * 1024 * 1024


def _localize_cover(src_url: str) -> str | None:
    """Скачивает обложку с src_url в _pending/, возвращает локальный путь или None при ошибке."""
    pending = _media_root() / "apartments" / "_pending"
    pending.mkdir(parents=True, exist_ok=True)
    # GC: удаляем файлы старше 24 ч
    cutoff = time.time() - 24 * 3600
    for old in pending.iterdir():
        try:
            if old.is_file() and old.stat().st_mtime < cutoff:
                old.unlink()
        except OSError:
            pass
    try:
        with httpx.Client(timeout=10.0, follow_redirects=True) as c:
            r = c.get(src_url)
            r.raise_for_status()
            ctype = (r.headers.get("content-type") or "").split(";")[0].strip().lower()
            ext = _ALLOWED_COVER_TYPES.get(ctype)
            if ext is None:
                return None
            name = f"{uuid.uuid4().hex}.{ext}"
            (pending / name).write_bytes(r.content)
            return f"/media/apartments/_pending/{name}"
    except Exception:
        return None


@router.post("/{apt_id}/cover")
async def upload_cover(
    apt_id: int,
    file: UploadFile = File(...),
    _: dict = Depends(require_role("owner", "admin")),
):
    ctype = (file.content_type or "").split(";", 1)[0].strip().lower()
    ext = _ALLOWED_COVER_TYPES.get(ctype)
    if ext is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Поддерживаются только jpeg/png/webp",
        )
    data = await file.read()
    if len(data) > _MAX_COVER_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Файл больше 5 МБ",
        )
    with get_conn() as conn:
        if _row(conn, apt_id) is None:
            raise HTTPException(status_code=404, detail="Квартира не найдена")
        target_dir = _media_root() / "apartments" / str(apt_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"cover.{ext}"
        # write to temp then atomic-rename, чтобы не остаться без cover при OSError
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_bytes(data)
        for old in target_dir.glob("cover.*"):
            if old.name == tmp.name:
                continue
            try:
                old.unlink()
            except OSError:
                pass
        os.replace(tmp, target)
        url = f"/media/apartments/{apt_id}/cover.{ext}"
        conn.execute("UPDATE apartments SET cover_url = ? WHERE id = ?", (url, apt_id))
    return {"cover_url": url}


@router.delete("/{apt_id}/cover", status_code=status.HTTP_204_NO_CONTENT)
def delete_cover(
    apt_id: int,
    _: dict = Depends(require_role("owner", "admin")),
):
    with get_conn() as conn:
        if _row(conn, apt_id) is None:
            raise HTTPException(status_code=404, detail="Квартира не найдена")
        target_dir = _media_root() / "apartments" / str(apt_id)
        if target_dir.exists():
            for old in target_dir.glob("cover.*"):
                try:
                    old.unlink()
                except OSError:
                    pass
        conn.execute("UPDATE apartments SET cover_url = NULL WHERE id = ?", (apt_id,))
    return None


@router.post("/{apt_id}/mark-dirty")
def mark_dirty(
    apt_id: int,
    payload: CleaningDueIn,
    _: dict = Depends(require_role("owner", "admin")),
):
    due_iso = payload.cleaning_due_at.isoformat(timespec="seconds")
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE apartments SET needs_cleaning = 1, cleaning_due_at = ? WHERE id = ?",
            (due_iso, apt_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Квартира не найдена"
            )
        row = _row(conn, apt_id)
    return dict(row)


@router.post("/{apt_id}/mark-clean")
def mark_clean(apt_id: int, _: dict = Depends(require_role("owner", "admin", "maid"))):
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE apartments SET needs_cleaning = 0, cleaning_due_at = NULL WHERE id = ?",
            (apt_id,),
        )
        if cur.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Квартира не найдена"
            )
        row = _row(conn, apt_id)
    return dict(row)
