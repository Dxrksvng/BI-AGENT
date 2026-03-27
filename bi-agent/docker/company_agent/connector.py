"""
docker/company_agent/connector.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BI Agent — Company Docker Agent

Runs inside the company's own server.
Connects to MySQL/PostgreSQL, queries tables on schedule,
and sends data to the BI Agent API automatically.

DB credentials never leave the company server.
Only query results are transmitted over HTTPS.

Usage:
    python connector.py
    # or via Docker:
    docker run -v $(pwd)/config.yaml:/config/config.yaml bi-agent-connector
"""

import os
import json
import time
import schedule
import requests
import pandas as pd
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    import subprocess
    subprocess.run(["pip", "install", "pyyaml"], check=True)
    import yaml

try:
    from sqlalchemy import create_engine, text
except ImportError:
    import subprocess
    subprocess.run(["pip", "install", "sqlalchemy", "psycopg2-binary", "pymysql"], check=True)
    from sqlalchemy import create_engine, text


# ─── Load Config ─────────────────────────────────────────────────────────────

def load_config() -> dict:
    paths = [
        "/config/config.yaml",          # Docker mount path
        "config.yaml",                  # local dev
        os.path.expanduser("~/config.yaml"),
    ]
    for p in paths:
        if Path(p).exists():
            with open(p) as f:
                return yaml.safe_load(f)
    raise FileNotFoundError("config.yaml not found. Mount it at /config/config.yaml")


# ─── Database Connection ──────────────────────────────────────────────────────

def build_connection_url(db: dict) -> str:
    db_type = db["type"].lower()
    host    = db["host"]
    port    = db.get("port", 5432 if db_type == "postgres" else 3306)
    name    = db["name"]
    user    = db["username"]
    pw      = db["password"]

    if db_type in ("postgres", "postgresql"):
        return f"postgresql+psycopg2://{user}:{pw}@{host}:{port}/{name}"
    elif db_type == "mysql":
        return f"mysql+pymysql://{user}:{pw}@{host}:{port}/{name}"
    else:
        raise ValueError(f"Unsupported database type: {db_type}")


def fetch_table(engine, table_name: str, limit: int = 10000) -> pd.DataFrame:
    query = text(f"SELECT * FROM {table_name} LIMIT :limit")
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"limit": limit})
    return df


# ─── Send to BI Agent ─────────────────────────────────────────────────────────

def push_to_bi_agent(df: pd.DataFrame, table_name: str, config: dict) -> dict:
    agent_cfg    = config["agent"]
    api_url      = agent_cfg["api_url"].rstrip("/")
    api_key      = agent_cfg["api_key"]
    company_name = agent_cfg.get("company_name", "Company")
    industry     = agent_cfg.get("industry", "general")

    payload = {
        "table_name": table_name,
        "data":       df.to_dict(orient="records"),
        "row_count":  len(df),
        "synced_at":  datetime.utcnow().isoformat(),
    }

    headers = {
        "X-API-Key":  api_key,
        "X-Company":  company_name,
        "X-Industry": industry,
        "Content-Type": "application/json",
    }

    resp = requests.post(
        f"{api_url}/ingest/push",
        json=payload,
        headers=headers,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


# ─── Main Sync Job ────────────────────────────────────────────────────────────

def sync_all_tables(config: dict):
    db_cfg  = config["database"]
    tables  = config["agent"].get("tables", [])

    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting sync...")

    try:
        url    = build_connection_url(db_cfg)
        engine = create_engine(url, pool_pre_ping=True)
        print(f"Connected to {db_cfg['type']} at {db_cfg['host']}")
    except Exception as e:
        print(f"DB connection failed: {e}")
        return

    for table in tables:
        try:
            print(f"  Fetching {table}...")
            df = fetch_table(engine, table)
            print(f"  {table}: {len(df)} rows, {len(df.columns)} columns")

            result = push_to_bi_agent(df, table, config)
            print(f"  Pushed to BI Agent — job_id: {result.get('job_id', '?')[:8]}...")

        except Exception as e:
            print(f"  Error syncing {table}: {e}")

    engine.dispose()
    print(f"Sync complete — {len(tables)} table(s) processed")


# ─── Scheduler ───────────────────────────────────────────────────────────────

def main():
    config       = load_config()
    agent_cfg    = config["agent"]
    interval_min = agent_cfg.get("sync_interval_minutes", 60)
    sync_time    = agent_cfg.get("sync_time", "08:00")

    print("BI Agent — Docker Connector")
    print(f"Database: {config['database']['type']} @ {config['database']['host']}")
    print(f"Tables:   {', '.join(agent_cfg.get('tables', []))}")
    print(f"API:      {agent_cfg['api_url']}")
    print(f"Schedule: every {interval_min} min + daily at {sync_time}")
    print()

    # Run immediately on startup
    sync_all_tables(config)

    # Schedule daily at fixed time
    schedule.every().day.at(sync_time).do(sync_all_tables, config)

    # Also schedule by interval
    schedule.every(interval_min).minutes.do(sync_all_tables, config)

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
