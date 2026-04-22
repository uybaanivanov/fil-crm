"""Collect Artyom's booking dump into a single markdown document.

Artyom pasted 12 apartments' booking ledgers into Telegram. Each message
that starts with 🏡 is a new apartment. Subsequent messages without 🏡 are
continuations (Telegram splits long texts at ~4096 chars).
"""

import json
from pathlib import Path

SRC = Path("scripts/tg_dumps/artyom.json")
OUT = Path("docs/inbox/artyom_bookings.md")


def main():
    msgs = json.loads(SRC.read_text(encoding="utf-8"))

    listings = []
    apartments = []
    current = None

    for m in msgs:
        text = m["text"] or ""
        if not text:
            continue
        if text.startswith("🏡"):
            if current is not None:
                apartments.append(current)
            current = {"header_id": m["id"], "date": m["date"], "text": text}
        elif current is not None and text[:1].isdigit() or (current and text.startswith(("Счёт", "Счет", "+", "—"))):
            current["text"] += text
        elif "doska.ykt.ru" in text or "trk.mail.ru" in text:
            listings.append(text.strip())
        elif current is not None:
            # fallback: looks like a continuation if it's not a ssh-config blob and not a link
            if "HostName" in text or text.strip() in ("\\",):
                continue
            current["text"] += text

    if current is not None:
        apartments.append(current)

    seen_headers = set()
    deduped = []
    for ap in apartments:
        head = ap["text"].splitlines()[0].strip()
        if head in seen_headers:
            continue
        seen_headers.add(head)
        deduped.append(ap)
    apartments = deduped

    lines = []
    lines.append("# Данные от Артёма (Telegram, 2026-04-22)")
    lines.append("")
    lines.append(
        "Источник: чат с Artyom (tg id 474504117). Сообщения #5229–#5265. "
        "Ниже сырой дамп: 12 квартир с помесячными реестрами броней "
        "и 12 ссылок на объявления на doska.ykt.ru."
    )
    lines.append("")

    lines.append("## Объявления на doska.ykt.ru")
    lines.append("")
    for l in listings:
        lines.append(f"- {l}")
    lines.append("")

    lines.append("## Квартиры и брони")
    lines.append("")
    for i, ap in enumerate(apartments, 1):
        head = ap["text"].splitlines()[0].lstrip("🏡 ").strip()
        lines.append(f"### {i}. {head}")
        lines.append("")
        lines.append("```")
        lines.append(ap["text"])
        lines.append("```")
        lines.append("")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"apartments={len(apartments)} listings={len(listings)} -> {OUT}")


if __name__ == "__main__":
    main()
