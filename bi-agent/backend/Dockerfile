FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY connector.py .

VOLUME ["/config"]

CMD ["python", "connector.py"]
```

**`docker/company_agent/requirements.txt`:**
```
sqlalchemy
psycopg2-binary
pymysql
pandas
requests
pyyaml
schedule