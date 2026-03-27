FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for WeasyPrint + Node.js
RUN apt-get update && apt-get install -y \
    curl \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libcairo2 \
    libffi-dev \
    shared-mime-info \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir redis sqlalchemy psycopg2-binary

# Node deps for pptxgenjs
COPY services/package.json services/
RUN cd services && npm install pptxgenjs

# App code
COPY . .

# Create reports directory
RUN mkdir -p /app/reports /app/fonts

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
