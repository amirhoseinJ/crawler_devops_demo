# enqueue.py

import json
import os
import time
import redis
from datetime import datetime, timezone

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QUEUE_KEY = "crawl_queue"

DEFAULT_URL = os.getenv("CRAWL_URL", "https://www.varzesh3.com/")
DEFAULT_TARGET = os.getenv("CRAWL_TARGET", "فوتبال")
DELAY_SECONDS = float(os.getenv("CRAWL_DELAY_SECONDS", "5"))

# Heartbeat 
K_LAST_ENQUEUE_TS =  "crawler:last_enqueue_ts"

def main():
    r = redis.from_url(REDIS_URL, decode_responses=True)
    print(f"[scheduler] Sending jobs to {QUEUE_KEY} every {DELAY_SECONDS} seconds.")
    print(f"[scheduler] URL={DEFAULT_URL} TARGET={DEFAULT_TARGET}")

    while True:
        payload = json.dumps({"url": DEFAULT_URL, "target": DEFAULT_TARGET})
        r.rpush(QUEUE_KEY, payload)
        # Heartbeat: record when we last enqueued a job
        ts = datetime.now(timezone.utc).isoformat()
        r.set(K_LAST_ENQUEUE_TS, ts)
        print(f"[scheduler] enqueued: {DEFAULT_URL} (target='{DEFAULT_TARGET}') @ {ts}")
        time.sleep(DELAY_SECONDS)

if __name__ == "__main__":
    main()
