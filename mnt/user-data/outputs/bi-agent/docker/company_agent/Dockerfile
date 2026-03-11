FROM python:3.11-slim

WORKDIR /app

# ติดตั้ง dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY connector.py .

# Mount config จากภายนอก (บริษัทจะสร้างไฟล์นี้เอง)
VOLUME ["/config"]

ENV CONFIG_PATH=/config/config.yaml

CMD ["python", "connector.py"]
