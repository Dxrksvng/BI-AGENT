"""
docker/company_agent/connector.py
ตัวนี้คือ Docker container ที่บริษัทโหลดไปรันใน server ตัวเอง

ทำหน้าที่:
  1. อ่าน config.yaml (connection string ของบริษัท)
  2. เชื่อมต่อ database
  3. ดึงข้อมูลตาม schedule
  4. ส่งมาที่ BI Agent API (ฝั่งคุณ)

บริษัทไม่ต้องส่ง password มาที่ cloud โดยตรง
ข้อมูลถูกเข้ารหัสด้วย HTTPS
"""

import os
import yaml
import requests
import pandas as pd
import sqlalchemy
import schedule
import time
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("company-agent")

# โหลด config จากไฟล์ (mount เข้า Docker volume)
CONFIG_PATH = os.getenv("CONFIG_PATH", "/config/config.yaml")


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def build_engine(cfg: dict):
    db = cfg["database"]
    if db["type"] == "postgres":
        url = f"postgresql://{db['username']}:{db['password']}@{db['host']}:{db['port']}/{db['name']}"
    elif db["type"] == "mysql":
        url = f"mysql+pymysql://{db['username']}:{db['password']}@{db['host']}:{db['port']}/{db['name']}"
    else:
        raise ValueError(f"ไม่รองรับ db type: {db['type']}")

    return sqlalchemy.create_engine(url, connect_args={"connect_timeout": 10})


def sync_tables(cfg: dict, engine):
    """ดึงข้อมูลจากทุกตารางที่กำหนดใน config แล้วส่งไป API"""
    api_url = cfg["agent"]["api_url"]   # URL ของ BI Agent ของคุณ
    api_key = cfg["agent"]["api_key"]   # API Key ที่ออกให้บริษัทนี้
    tables  = cfg["agent"]["tables"]    # รายชื่อตารางที่ต้องการ sync

    headers = {
        "X-API-Key":    api_key,
        "Content-Type": "application/json",
    }

    for table in tables:
        try:
            logger.info(f"กำลังดึงข้อมูลจากตาราง: {table}")
            df = pd.read_sql(f'SELECT * FROM "{table}" LIMIT 100000', engine)

            # แปลงเป็น JSON แล้วส่งไป API
            payload = {
                "table_name": table,
                "data":       df.to_dict(orient="records"),
                "row_count":  len(df),
                "synced_at":  datetime.utcnow().isoformat(),
            }

            resp = requests.post(
                f"{api_url}/ingest/push",
                json=payload,
                headers=headers,
                timeout=60,
            )
            resp.raise_for_status()
            logger.info(f"ส่งข้อมูล '{table}' สำเร็จ: {len(df)} แถว → job_id={resp.json().get('job_id')}")

        except Exception as e:
            logger.error(f"ส่งข้อมูล '{table}' ล้มเหลว: {e}")


def main():
    cfg    = load_config()
    engine = build_engine(cfg)

    interval_minutes = cfg["agent"].get("sync_interval_minutes", 60)
    logger.info(f"BI Agent Connector เริ่มทำงาน — sync ทุก {interval_minutes} นาที")

    # รัน sync ครั้งแรกทันที
    sync_tables(cfg, engine)

    # แล้วรัน schedule ต่อไป
    schedule.every(interval_minutes).minutes.do(sync_tables, cfg=cfg, engine=engine)

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
