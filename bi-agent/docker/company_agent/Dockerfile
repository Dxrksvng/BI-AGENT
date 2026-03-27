FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    sqlalchemy==2.0.30 \
    psycopg2-binary==2.9.9 \
    pymysql==1.1.1 \
    pandas==2.2.2 \
    requests==2.32.3 \
    schedule==1.2.2 \
    pyyaml==6.0.1

COPY connector.py .

VOLUME ["/config"]

CMD ["python", "connector.py"]
