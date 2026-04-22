import logging
import time
from datetime import date

from backend.db import get_conn

TICK_SECONDS = 600

log = logging.getLogger("worker")


def close_past_active_bookings() -> int:
    today = date.today().isoformat()
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE bookings SET status='completed' "
            "WHERE status='active' AND check_out <= ?",
            (today,),
        )
        return cur.rowcount


def tick() -> None:
    n = close_past_active_bookings()
    if n:
        log.info("closed %d past active bookings", n)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    log.info("worker started, tick=%ss", TICK_SECONDS)
    while True:
        try:
            tick()
        except Exception:
            log.exception("tick failed")
        time.sleep(TICK_SECONDS)


if __name__ == "__main__":
    main()
