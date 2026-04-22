import asyncio
import os
from telethon import TelegramClient

API_ID = int(os.environ["TELEGRAM_API_ID"])
API_HASH = os.environ["TELEGRAM_API_HASH"]


async def main():
    client = TelegramClient("account", API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        raise SystemExit("not authorized")

    async for dialog in client.iter_dialogs(limit=30):
        name = dialog.name or ""
        last = dialog.message
        preview = (last.message or "").replace("\n", " ")[:80] if last else ""
        date = last.date.isoformat() if last else ""
        print(f"{dialog.id}\t{date}\t{name!r}\t{preview!r}")

    await client.disconnect()


asyncio.run(main())
