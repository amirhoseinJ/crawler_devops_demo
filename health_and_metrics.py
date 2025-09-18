# health.py

import os
import redis
from datetime import datetime, timezone
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse, Response

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Counters
K_FETCH =  "crawler:fetch_total"
K_OK    = "crawler:success_total"
K_ERR   =  "crawler:error_total"

# heartbeat 
K_LAST_STATUS    =  "crawler:last_status"       
K_LAST_TS        =  "crawler:last_ts"             
K_LAST_ERROR     =  "crawler:last_error"
K_LAST_ENQUEUE_TS = "crawler:last_enqueue_ts"    

# thresholds 
HEALTH_ENQUEUE_MAX_SECONDS = float(os.getenv("HEALTH_ENQUEUE_MAX_SECONDS", "20"))  
HEALTH_WORKER_MAX_SECONDS   = float(os.getenv("HEALTH_WORKER_MAX_SECONDS", "25"))   

app = FastAPI()

def get_redis():
    return redis.from_url(REDIS_URL, decode_responses=True)

def _parse_iso(ts: str | None):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return None

@app.get("/healthz")
def healthz():
    r = get_redis()

    fetch_total = int(r.get(K_FETCH) or 0)
    ok_total    = int(r.get(K_OK) or 0)
    err_total   = int(r.get(K_ERR) or 0)

    last_status = r.get(K_LAST_STATUS)
    last_error  = r.get(K_LAST_ERROR)
    job_ts_str  = r.get(K_LAST_TS)
    enq_ts_str  = r.get(K_LAST_ENQUEUE_TS)

    now = datetime.now(timezone.utc)

    job_ts = _parse_iso(job_ts_str)
    enq_ts = _parse_iso(enq_ts_str)


    scheduler_ok = (enq_ts is not None) and ((now - enq_ts).total_seconds() <= HEALTH_ENQUEUE_MAX_SECONDS)
    worker_ok    = (job_ts is not None) and ((now - job_ts).total_seconds() <= HEALTH_WORKER_MAX_SECONDS)

    overall_ok = scheduler_ok and worker_ok and (last_status == "ok")

    payload = {
        "status": "ok" if overall_ok else "error",
        "components": {
            "scheduler": "ok" if scheduler_ok else "stale_or_down",
            "worker": "ok" if worker_ok else "stale_or_down",
            "last_job_status": last_status or "unknown",
        },
        "timestamps": {
            "last_enqueue_ts": enq_ts_str,
            "last_job_ts": job_ts_str,
        },
        "counters": {
            "fetch_total": fetch_total,
            "success_total": ok_total,
            "error_total": err_total,
        },
    }
    if last_error:
        payload["last_error"] = last_error

    if overall_ok:
        return JSONResponse(payload, status_code=status.HTTP_200_OK)
    else:
        return JSONResponse(payload, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)

@app.get("/metrics")
def metrics():
    r = get_redis()
    fetch_total = int(r.get(K_FETCH) or 0)
    ok_total    = int(r.get(K_OK) or 0)
    err_total   = int(r.get(K_ERR) or 0)

    lines = [
        "# HELP crawler_fetch_total Total crawl fetch attempts.",
        "# TYPE crawler_fetch_total counter",
        f"crawler_fetch_total {fetch_total}",
        "# HELP crawler_success_total Total successful crawl executions.",
        "# TYPE crawler_success_total counter",
        f"crawler_success_total {ok_total}",
        "# HELP crawler_error_total Total failed crawl executions.",
        "# TYPE crawler_error_total counter",
        f"crawler_error_total {err_total}",
        "",
    ]
    body = "\n".join(lines)
    return Response(
        content=body,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
