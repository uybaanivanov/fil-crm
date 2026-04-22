"""Парсит брони Артёма из docs/inbox/artyom_bookings.md в TSV для ревью.

Выход:
  docs/inbox/artyom_bookings_parsed.tsv    — распознанные брони
  docs/inbox/artyom_bookings_unparsed.tsv  — строки ◾️/▪️ что не распознались

Логика года: идём сверху вниз по записям в блоке; при переходе
month_in < prev_month_in инкрементим year. Стартовый year подбираем
так, чтобы последняя запись оказалась в текущем году (TODAY_YEAR = 2026).

Самодостаточный — без импорта backend.
"""

import re
import sys
from datetime import date
from pathlib import Path

import yaml

MAPPING = Path("docs/inbox/apartment_mapping.yaml")
DUMP = Path("docs/inbox/artyom_bookings.md")
OUT_PARSED = Path("docs/inbox/artyom_bookings_parsed.tsv")
OUT_UNPARSED = Path("docs/inbox/artyom_bookings_unparsed.tsv")

TODAY_YEAR = 2026

# Строгий каноничный формат: ◾️[🧹]dd.mm[.]-dd.mm/<rest>
RE_CANON = re.compile(
    r"^[◾▪]️?\s*🧹?\s*"
    r"(\d{1,2})\.(\d{1,2})\.?"
    r"\s*[-–]\s*"
    r"(\d{1,2})\.(\d{1,2})"
    r"\s*/\s*(.+)$"
)

# Single-date вариант: ◾️dd.mm/<rest> (check_out = check_in + 1 сутки)
RE_SINGLE_DATE = re.compile(
    r"^[◾▪]️?\s*🧹?\s*"
    r"(\d{1,2})\.(\d{1,2})"
    r"\s*/\s*(.+)$"
)

# Краткий (только Николаева 11/4а, первые записи): ▪️DD(сутки)/... или ▪️D-D/...
# Тут dates без месяца; месяц подставляем из секции.
RE_SHORT = re.compile(
    r"^[◾▪]️?\s*🧹?\s*"
    r"(\d{1,2})(?:\s*[-–]\s*(\d{1,2}))?"
    r"\s*(?:\(сутки\))?\s*/\s*(.+)$"
)

PHONE_RE = re.compile(
    r"(\+7[\s\xa0\-‑]?\d{3}[\s\xa0\-‑]?\d{3}[\s\xa0\-‑]?\d{2}[\s\xa0\-‑]?\d{2}|"
    r"\+7\d{10}|8\d{10}|\b\d{11}\b)"
)


# Число с опциональным знаком '+' и опциональным '₽' после.
# Число либо ≥ 1000, либо обязательно с ₽ (чтобы 2сутки/1гость не считались ценой).
MONEY_RE = re.compile(
    r"(?P<sign>[+])?\s*(?P<num>\d{1,2}[.,]\d{3}|\d{3,6})\s*(?P<rub>₽)?"
)


def _parse_money_num(raw: str) -> int:
    return int(raw.replace(".", "").replace(",", ""))


def extract_prices(rest: str) -> tuple[int | None, int]:
    """Вернуть (main_price, extras_sum) из свободного текста.

    Правила:
      - Первое число без знака '+' — main.
      - Числа с '+' — extras (часовые продления, доплаты).
      - Число без ₽ считается только если оно >= 1000.
    """
    main: int | None = None
    extras = 0
    for m in MONEY_RE.finditer(rest):
        num = _parse_money_num(m.group("num"))
        has_rub = m.group("rub") is not None
        if not has_rub and num < 1000:
            continue
        if m.group("sign") == "+":
            extras += num
        elif main is None:
            main = num
    return main, extras


def parse_booking_line(
    line: str, section_month: int | None
) -> dict | None:
    """Вернуть dict или None, если строку парсить не удалось."""
    m = RE_CANON.match(line)
    if m:
        d1, m1, d2, m2, rest = m.groups()
        return {
            "d_in": int(d1),
            "m_in": int(m1),
            "d_out": int(d2),
            "m_out": int(m2),
            "rest": rest,
        }
    m = RE_SINGLE_DATE.match(line)
    if m:
        d1, m1, rest = m.groups()
        d1_i, m1_i = int(d1), int(m1)
        # check_out = check_in + 1 день; перенос месяца не отрабатываем, просто m_out=m_in
        return {
            "d_in": d1_i,
            "m_in": m1_i,
            "d_out": d1_i + 1,
            "m_out": m1_i,
            "rest": rest,
        }
    if section_month is not None:
        m = RE_SHORT.match(line)
        if m:
            d1, d2, rest = m.groups()
            d1 = int(d1)
            d2 = int(d2) if d2 else d1 + 1  # сутки без второй даты
            return {
                "d_in": d1,
                "m_in": section_month,
                "d_out": d2,
                "m_out": section_month,
                "rest": rest,
            }
    return None


MONTHS = {
    "январ": 1, "феврал": 2, "март": 3, "апрел": 4, "впрел": 4,
    "мая": 5, "май": 5, "июн": 6, "июл": 7, "август": 8,
    "сентябр": 9, "октябр": 10, "ноябр": 11, "декабр": 12,
}


def detect_section_month(line: str) -> int | None:
    low = line.lower()
    for key, num in MONTHS.items():
        if key in low:
            return num
    return None


def parse_rest(rest: str) -> dict:
    """Выдернуть phone + price (main + extras) + оставить остальное как notes."""
    text = rest
    phone_match = PHONE_RE.search(text)
    phone = phone_match.group(0).strip() if phone_match else None
    if phone:
        text = (text[: phone_match.start()] + text[phone_match.end():])

    main_price, hourly_extra = extract_prices(text)
    if main_price is None:
        total_price = None
    else:
        total_price = main_price + hourly_extra

    # Чистим notes от уже учтённых сумм
    clean = MONEY_RE.sub(" ", text)
    other = re.sub(r"\s+", " ", clean).strip(" ,/")

    return {
        "total_price": total_price,
        "hourly_extra": hourly_extra,
        "phone": phone,
        "other": other,
        "price_token": rest[:80],
    }


def _safe_date(y: int, m: int, d: int) -> date | None:
    """date() с подстраховкой 29.02 в невисокосный год и прочих перескоков."""
    from calendar import monthrange

    try:
        return date(y, m, d)
    except ValueError:
        if 1 <= m <= 12:
            last_day = monthrange(y, m)[1]
            if d > last_day:
                return date(y, m, last_day)
    return None


def make_dates(
    rec: dict, current_year: int
) -> tuple[str, str]:
    y_in = current_year
    # check_out: если месяц меньше чем у check_in — значит перешли через Новый год
    y_out = y_in + 1 if rec["m_out"] < rec["m_in"] else y_in
    di = _safe_date(y_in, rec["m_in"], rec["d_in"])
    do = _safe_date(y_out, rec["m_out"], rec["d_out"])
    if di is None or do is None:
        return "", ""
    return di.isoformat(), do.isoformat()


def process_block(apt_id: int, text: str) -> tuple[list[dict], list[str]]:
    parsed_entries: list[dict] = []
    unparsed_lines: list[str] = []

    section_month: int | None = None
    current_year: int | None = None  # выставим после первого прогона
    # Первый проход: собрать все брони с m_in, без year. Потом оценим стартовый год.
    records: list[dict] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if not stripped.startswith(("◾", "▪")):
            sm = detect_section_month(stripped)
            if sm is not None:
                section_month = sm
            continue
        rec = parse_booking_line(stripped, section_month)
        if rec is None:
            unparsed_lines.append(stripped)
            continue
        rec["raw"] = stripped
        records.append(rec)

    if not records:
        return [], unparsed_lines

    # Оценить стартовый год: идём сверху, year+=1 при month_in < prev_month.
    # Потом сдвигаем стартовый чтобы last = TODAY_YEAR.
    year_offsets = [0]
    for i in range(1, len(records)):
        prev = records[i - 1]["m_in"]
        cur = records[i]["m_in"]
        offset = year_offsets[-1]
        # если откат явный (разница >= 6 месяцев назад) — считаем year+=1
        # маленькие откаты (1-2 месяца) — считаем опечаткой, год не меняем
        if cur < prev and (prev - cur) >= 6:
            offset += 1
        year_offsets.append(offset)

    last_offset = year_offsets[-1]
    start_year = TODAY_YEAR - last_offset

    for rec, off in zip(records, year_offsets):
        year = start_year + off
        d_in, d_out = make_dates(rec, year)
        fields = parse_rest(rec["rest"])
        parsed_entries.append(
            {
                "apt_id": apt_id,
                "check_in": d_in,
                "check_out": d_out,
                "total_price": fields["total_price"],
                "hourly_extra": fields["hourly_extra"],
                "phone": fields["phone"] or "",
                "notes": fields["other"],
                "raw": rec["raw"],
            }
        )

    return parsed_entries, unparsed_lines


def main() -> int:
    mapping = yaml.safe_load(MAPPING.read_text(encoding="utf-8"))
    text = DUMP.read_text(encoding="utf-8")
    section = text.split("## Квартиры и брони", 1)[1]
    blocks = re.findall(r"```\n(.*?)\n```", section, flags=re.DOTALL)

    all_parsed: list[dict] = []
    all_unparsed: list[tuple[int, str]] = []

    for i, entry in enumerate(mapping):
        if entry.get("status") != "confirmed":
            continue
        apt_id = entry["apt_id"]
        parsed, unparsed = process_block(apt_id, blocks[i])
        print(f"apt_id={apt_id:2}  parsed={len(parsed):3}  unparsed={len(unparsed):2}")
        all_parsed.extend(parsed)
        all_unparsed.extend((apt_id, l) for l in unparsed)

    OUT_PARSED.parent.mkdir(parents=True, exist_ok=True)
    header = [
        "apt_id", "check_in", "check_out", "total_price",
        "hourly_extra", "phone", "notes", "raw",
    ]
    with OUT_PARSED.open("w", encoding="utf-8") as f:
        f.write("\t".join(header) + "\n")
        for e in all_parsed:
            f.write(
                "\t".join(
                    [
                        str(e["apt_id"]),
                        e["check_in"],
                        e["check_out"],
                        "" if e["total_price"] is None else str(e["total_price"]),
                        str(e["hourly_extra"]) if e["hourly_extra"] else "",
                        e["phone"],
                        e["notes"].replace("\t", " "),
                        e["raw"].replace("\t", " "),
                    ]
                )
                + "\n"
            )
    with OUT_UNPARSED.open("w", encoding="utf-8") as f:
        f.write("apt_id\traw\n")
        for apt_id, raw in all_unparsed:
            f.write(f"{apt_id}\t{raw}\n")

    print(
        f"\nTotal parsed: {len(all_parsed)}  unparsed: {len(all_unparsed)}  "
        f"→ {OUT_PARSED}, {OUT_UNPARSED}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
