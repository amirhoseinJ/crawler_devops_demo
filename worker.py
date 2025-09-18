# worker.py

import json
import os
import time
import unicodedata
from datetime import datetime, timezone

import psycopg
import redis
import requests
from bs4 import BeautifulSoup


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
POSTGRES_DSN = os.getenv("POSTGRES_DSN", "postgresql://postgres:postgres@localhost:5432/postgres")

QUEUE_KEY =  "crawl_queue"
# counters
K_FETCH = "crawler:fetch_total"
K_OK  = "crawler:success_total"
K_ERR  = "crawler:error_total"


# health
K_LAST_STATUS = "crawler:last_status"  # "ok" | "error"
K_LAST_TS     =  "crawler:last_ts"        # ISO-8601
K_LAST_ERROR  =  "crawler:last_error"   # last error message (optional)



HEADERS = {
    "User-Agent": ("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36")
}
REQUEST_TIMEOUT = 15


def normalize(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    return (s.replace("ي", "ی")
            .replace("ى", "ی")
            .replace("ك", "ک")
            .replace("\u200c", " ")
            .replace("\u200f", "")
            .replace("\u200e", ""))


def ensure_table(conn: psycopg.Connection):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS crawl_metrics (
              "timestamp" TIMESTAMPTZ NOT NULL DEFAULT now(),
              "count" INTEGER,
              crawler_fetch_total BIGINT NOT NULL,
              crawler_success_total BIGINT NOT NULL,
              crawler_error_total BIGINT NOT NULL
            );
        """)
        conn.commit()


def parse_visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "noscript"]):
        t.decompose()
    return " ".join(s.strip() for s in soup.stripped_strings if s.strip())


def crawl_and_count(url: str, target: str) -> int:
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    # Prefer declared encoding, or fall back to apparent if available
    resp.encoding = resp.apparent_encoding or resp.encoding or "utf-8"
    text = parse_visible_text(resp.text)
    return normalize(text).count(normalize(target))


def main():
    r = redis.from_url(REDIS_URL, decode_responses=True)
    with psycopg.connect(POSTGRES_DSN) as conn:
        ensure_table(conn)
        print(f"[worker] connected to Postgres and Redis. Waiting on queue: {QUEUE_KEY}")

        while True:
            # Block until a job arrives: job payload is JSON: {"url": "...", "target": "..."}
            _, raw = r.blpop(QUEUE_KEY, timeout=0)  # 0 = block forever
            ts = datetime.now(timezone.utc)

            try:
                job = json.loads(raw)
                url = job["url"]
                target = job.get("target", "")
            except Exception as e:
                # Malformed job -> count as error, record row with count NULL
                r.incr(K_FETCH)
                r.incr(K_ERR)
                fetch_total   = int(r.get(K_FETCH) or 0)
                success_total = int(r.get(K_OK) or 0)
                error_total   = int(r.get(K_ERR) or 0)


                r.mset({K_LAST_STATUS: "error", K_LAST_TS: ts.isoformat(), K_LAST_ERROR: f"bad job: {e}"})
                

                with conn.cursor() as cur:
                    cur.execute(
                        'INSERT INTO crawl_metrics ("timestamp", "count", '
                        'crawler_fetch_total, crawler_success_total, crawler_error_total) '
                        'VALUES (%s, %s, %s, %s, %s);',
                        (ts, None, fetch_total, success_total, error_total)
                    )
                    conn.commit()
                print(f"[worker] bad job payload; recorded error: {e}")
                continue

            # Count a fetch attempt before the HTTP request
            r.incr(K_FETCH)

            count_value = None
            had_error = False
            try:
                count_value = crawl_and_count(url, target)
                r.incr(K_OK)
                print(f"[worker] OK: {url} — occurrences of '{target}': {count_value}")
                
                
                r.mset({K_LAST_STATUS: "ok", K_LAST_TS: ts.isoformat(), K_LAST_ERROR: ""})

            except Exception as e:
                r.incr(K_ERR)
                had_error = True
                print(f"[worker] ERROR fetching {url}: {e}")

                r.mset({K_LAST_STATUS: "error", K_LAST_TS: ts.isoformat(), K_LAST_ERROR: str(e)})

            # Read current totals and insert a row
            fetch_total   = int(r.get(K_FETCH) or 0)
            success_total = int(r.get(K_OK) or 0)
            error_total   = int(r.get(K_ERR) or 0)

            with conn.cursor() as cur:
                cur.execute(
                    'INSERT INTO crawl_metrics ("timestamp", "count", '
                    'crawler_fetch_total, crawler_success_total, crawler_error_total) '
                    'VALUES (%s, %s, %s, %s, %s);',
                    (ts, count_value, fetch_total, success_total, error_total)
                )
                conn.commit()

            if not had_error:
                time.sleep(0.1)


if __name__ == "__main__":
    main()
