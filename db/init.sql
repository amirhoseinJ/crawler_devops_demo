CREATE TABLE IF NOT EXISTS crawl_metrics (
  "timestamp" TIMESTAMPTZ NOT NULL DEFAULT now(),
  "count" INTEGER,
  crawler_fetch_total BIGINT NOT NULL,
  crawler_success_total BIGINT NOT NULL,
  crawler_error_total BIGINT NOT NULL
);
