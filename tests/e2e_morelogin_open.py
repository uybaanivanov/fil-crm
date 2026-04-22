"""Smoke MoreLogin: запусти, увидишь окно MoreLogin-профиля, Enter — закроется."""
import asyncio

from backend.morelogin import ENV_ID, start_profile, stop_profile


async def main():
    eid = ENV_ID or input("MORELOGIN_ENV_ID не задан, введи envId: ").strip()
    input(f"Стартовать профиль {eid}? [Enter]")
    session = await start_profile(eid)
    print(f"CDP URL: {session.cdp_url}")
    print(f"debug port: {session.debug_port}")
    input("Профиль открыт. Enter для закрытия...")
    await stop_profile(eid)
    print("OK")


if __name__ == "__main__":
    asyncio.run(main())
