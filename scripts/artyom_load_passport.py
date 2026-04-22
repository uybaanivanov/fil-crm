"""Залить паспортные поля Артёма в apartments для смапленных квартир.

Читает:
  docs/inbox/apartment_mapping.yaml (confirmed только)
  docs/inbox/artyom_bookings.md (заголовки ### 1. ...)

Парсит первую строку каждого бронь-блока (она же заголовок-паспорт
в исходнике Telegram) и обновляет apartments.{entrance, apt_number,
intercom_code, safe_code, utility_account, price_weekday, price_weekend}.

Самодостаточный: backend не импортируется.

uv run --with pyyaml python scripts/artyom_load_passport.py [--dry-run]
"""

import argparse
import re
import sqlite3
import sys
from pathlib import Path

import yaml

DB = Path("db.sqlite3")
MAPPING = Path("docs/inbox/apartment_mapping.yaml")
DUMP = Path("docs/inbox/artyom_bookings.md")


def load_raw_headers() -> list[str]:
    """Return passport-prefix of each ``` fenced apartment block (всё до первой
    записи брони: ◾️/▪️/«Счёт»/«Сентябрь»)."""
    text = DUMP.read_text(encoding="utf-8")
    block = text.split("## Квартиры и брони", 1)[1]
    blocks = re.findall(r"```\n(.*?)\n```", block, flags=re.DOTALL)
    cut_re = re.compile(
        r"(◾️|▪️|Счёт|Счет|Сентябрь|Октябрь|Ноябрь|Декабрь|"
        r"Январь|Февраль|Март|Апрель|Май|Июнь|Июль|Август)"
    )
    out = []
    for b in blocks:
        m = cut_re.search(b)
        prefix = b[: m.start()] if m else b
        out.append(prefix.strip())
    return out


# --- parsers ---------------------------------------------------------------


def parse_entrance(s: str) -> str | None:
    """'2 подъезд' or 'подъезд 2' or '2под' → '2'."""
    m = re.search(r"(\d+)\s*подъезд", s, re.I) or re.search(
        r"подъезд\s*(\d+)", s, re.I
    ) or re.search(r"(\d+)\s*под\b", s, re.I)
    return m.group(1) if m else None


def parse_apt_number(s: str) -> str | None:
    """'104 кв', 'кв 5', 'кв165', '156кв', '79кв'. Номер может быть '55б'.

    Требуем что номер — цифры с опциональным хвостом из кириллической буквы,
    иначе regex лапает слова вроде 'Сейф' в '104 кв Сейф 0202'."""
    m = re.search(r"(?:^|[\s,])(\d+[а-я]?)\s*кв\.?\b", s, re.I)
    if m:
        return m.group(1)
    m = re.search(r"\bкв\.?\s*(\d+[а-я]?)\b", s, re.I)
    return m.group(1) if m else None


def parse_intercom(s: str) -> str | None:
    """'Домофон 27049', 'домофон #2020', 'домофон 104', '#2018', '#5623'."""
    m = re.search(r"домофон\s*#?\s*(\d+)", s, re.I)
    if m:
        return m.group(1)
    # «104 звонить домофон»
    m = re.search(r"(\d{3,})\s*звонить\s*домофон", s, re.I)
    if m:
        return m.group(1)
    # «#2018» в свободной форме (только если есть ровно один)
    hits = re.findall(r"#(\d{3,})", s)
    if len(hits) == 1:
        return hits[0]
    return None


def parse_safe(s: str) -> str | None:
    """'Сейф 0202', 'сейф 0056', 'сейф 1205'. Может встречаться дважды — берём первое."""
    m = re.search(r"сейф\s*(\d{3,})", s, re.I)
    return m.group(1) if m else None


def parse_utility_account(s: str) -> str | None:
    """'ЛС 141111935'."""
    m = re.search(r"ЛС\s*(\d+)", s, re.I)
    return m.group(1) if m else None


_PRICE = r"(\d{3,5})"


def parse_price_weekday(s: str) -> int | None:
    m = re.search(rf"Будни\s*[-–]?\s*{_PRICE}\s*₽", s, re.I)
    return int(m.group(1)) if m else None


def parse_price_weekend(s: str) -> int | None:
    m = re.search(rf"Пт/сб\s*[-–]?\s*{_PRICE}\s*₽", s, re.I)
    return int(m.group(1)) if m else None


def parse_passport(header: str) -> dict:
    return {
        "entrance": parse_entrance(header),
        "apt_number": parse_apt_number(header),
        "intercom_code": parse_intercom(header),
        "safe_code": parse_safe(header),
        "utility_account": parse_utility_account(header),
        "price_weekday": parse_price_weekday(header),
        "price_weekend": parse_price_weekend(header),
    }


# --- main ------------------------------------------------------------------


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    mapping = yaml.safe_load(MAPPING.read_text(encoding="utf-8"))
    headers = load_raw_headers()

    if len(mapping) != len(headers):
        print(
            f"WARN: mapping has {len(mapping)} entries, "
            f"dump has {len(headers)} apartments — порядок может разойтись"
        )

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    updated = skipped = 0
    for i, entry in enumerate(mapping):
        if entry.get("status") != "confirmed":
            print(f"[{i+1:2}] SKIP {entry['artyom_header'][:60]!r} → {entry.get('status')}")
            skipped += 1
            continue
        apt_id = entry["apt_id"]
        raw_header = headers[i] if i < len(headers) else entry["artyom_header"]
        fields = parse_passport(raw_header)
        present = {k: v for k, v in fields.items() if v is not None}

        print(f"[{i+1:2}] apt_id={apt_id}  header={raw_header[:70]!r}")
        for k, v in fields.items():
            mark = "+" if v is not None else " "
            print(f"      {mark} {k:20} = {v!r}")
        if not present:
            print("      (ничего не распозналось — пропускаю)")
            skipped += 1
            continue

        if not args.dry_run:
            set_clause = ", ".join(f"{k} = ?" for k in present)
            conn.execute(
                f"UPDATE apartments SET {set_clause} WHERE id = ?",
                list(present.values()) + [apt_id],
            )
        updated += 1

    if not args.dry_run:
        conn.commit()
    conn.close()

    mode = "(dry-run)" if args.dry_run else ""
    print(f"\nupdated={updated} skipped={skipped} {mode}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
