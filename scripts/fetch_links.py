import asyncio
import os
import re

from telethon import TelegramClient


URL_RE = re.compile(r"https?://\S+")
KEEP_RE = re.compile(r"(doska\.ykt\.ru/\d+|youla\.ru/|trk\.mail\.ru/)")
SKIP_RE = re.compile(r"doska\.ykt\.ru/app$")


async def main():
    api_id = int(os.environ["TELEGRAM_API_ID"])
    api_hash = os.environ["TELEGRAM_API_HASH"]
    async with TelegramClient("account", api_id, api_hash) as client:
        raw = []
        async for msg in client.iter_messages(474504117, limit=40):
            if not msg.message:
                continue
            for u in URL_RE.findall(msg.message):
                u = u.rstrip(".,);")
                if SKIP_RE.search(u):
                    continue
                if KEEP_RE.search(u):
                    raw.append((msg.id, u))
        # oldest → newest (chronological sent order)
        raw.sort()
        seen = set()
        uniq = [u for _, u in raw if not (u in seen or seen.add(u))]
        path = "tests/e2e/fixtures/listing_urls.txt"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write("\n".join(uniq) + "\n")
        print(f"wrote {len(uniq)} links to {path}")
        for u in uniq:
            print(u)


asyncio.run(main())
