import asyncio
import json
import os
import sys
from telethon import TelegramClient

API_ID = int(os.environ["TELEGRAM_API_ID"])
API_HASH = os.environ["TELEGRAM_API_HASH"]


async def main():
    peer_id = int(sys.argv[1])
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 500
    out_path = sys.argv[3]

    client = TelegramClient("account", API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        raise SystemExit("not authorized")

    entity = await client.get_entity(peer_id)
    rows = []
    async for m in client.iter_messages(entity, limit=limit):
        rows.append(
            {
                "id": m.id,
                "date": m.date.isoformat() if m.date else None,
                "from_id": getattr(m.sender_id, "__int__", lambda: m.sender_id)()
                if m.sender_id is not None
                else None,
                "out": bool(m.out),
                "text": m.message or "",
                "reply_to": m.reply_to_msg_id,
                "media": type(m.media).__name__ if m.media else None,
            }
        )
    rows.reverse()
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print(f"saved {len(rows)} messages -> {out_path}")

    await client.disconnect()


asyncio.run(main())
