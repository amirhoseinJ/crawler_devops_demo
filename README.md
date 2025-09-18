# A Simple Crawler (Redis queue + Postgres + FastAPI health/metrics)

- Pushes crawl jobs.
- Consumes jobs, writes metrics to Postgres, updates Redis counters.
- `/healthz` returns 200/503 based on freshness and last job status.
- `/metrics` exposes Prometheus counters.

## 1. Requirements
- Docker, Docker-compose, curl and jq (for API testing).
- On Ubuntu:
```bash
sudo apt install docker docker-compose curl jq -y
```

## 2. Clone the Repository

```
git clone https://github.com/amirhoseinJ/crawler_devops_demo.git
```
```
cd crawler_devops_demo
```

## 3. Environmet Variables
- If you want to override default variables, copy .env.example to .env and edit it accordingly. Otherwise, defaults will be used.
```
cp .env.example .env
```
- Table of editable variables:

| Service | Variable | Default Value |
|----------|----------|----------|
| Postgres   | POSTGRES_DB     | crawlerdb     |
| Postgres    | POSTGRES_USER     | crawleruser     |
| Postgres    | POSTGRES_PASSWORD   | postgres       |
| API   | API_PORT     | 8000     |
| API    | HEALTH_ENQUEUE_MAX_SECONDS     | 20     |
| API    | HEALTH_WORKER_MAX_SECONDS   | 25       |
| Crawler (worker)  | CRAWL_URL     | https://www.varzesh3.com/     |
| Crawler (worker)   | CRAWL_TARGET     | فوتبال     |
| Crawler (worker)   | CRAWL_DELAY_SECONDS   | 5       |