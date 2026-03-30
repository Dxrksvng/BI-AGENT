# BI-Agent

<p align="center">
  <img src="'/Users/jswvn/Desktop/missj/My-project/BI-AGENT/tests/ChatGPT Image 30 มี.ค. 2569 03_41_57.png'" width="600"/>
</p>
AI-Powered Business Intelligence Automation Platform

![Python](https://img.shields.io/badge/python-3.10-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-production-green)
![Docker](https://img.shields.io/badge/docker-ready-blue)
![AI](https://img.shields.io/badge/AI-Agent%20System-orange)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

# Overview

**BI-Agent** คือระบบ **AI Business Intelligence Automation Platform**

ที่สามารถเปลี่ยน

```
Raw Data → Business Insight → Executive Report
```

โดยอัตโนมัติ

ระบบถูกออกแบบให้เหมือน

```
AI Data Analyst
+ AI Strategy Consultant
+ AI Report Designer
```

รวมอยู่ใน pipeline เดียว

เหมาะสำหรับ

* Data Analysts
* Business Intelligence Teams
* Consulting workflows
* Automated executive reporting

---

# Core Capabilities

BI-Agent สามารถ

```
1. Ingest Data (CSV / SQL)
2. Run ETL + Data Quality Check
3. AI Insight Discovery
4. Executive-Level Analysis
5. Auto Design Reports
6. Export Dashboard / PPTX / PDF
```

ทั้งหมดทำงานผ่าน **AI Agent Pipeline**

---

# System Architecture (Netflix-Style)

```
                    ┌───────────────────────────┐
                    │        USER INTERFACE      │
                    │       Streamlit UI         │
                    └─────────────┬─────────────┘
                                  │
                                  ▼
                        ┌─────────────────┐
                        │   FASTAPI API   │
                        └───────┬─────────┘
                                │
                ┌───────────────┼─────────────────┐
                ▼               ▼                 ▼

        ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
        │ INGESTION     │ │ ETL PIPELINE │ │ AI ANALYSIS  │
        │ Layer         │ │ Pandas       │ │ LLM Engine   │
        └───────┬──────┘ └───────┬──────┘ └───────┬──────┘
                │                │                │
                ▼                ▼                ▼

        ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
        │ CONSULTING    │ │ DESIGN AGENT │ │ EXPORT LAYER │
        │ AGENT         │ │ Theme Engine │ │ PPTX / PDF   │
        └───────┬──────┘ └───────┬──────┘ └───────┬──────┘
                │                │                │
                ▼                ▼                ▼

        ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
        │ DASHBOARD     │ │ POWERPOINT   │ │ PDF REPORT   │
        │ Streamlit     │ │ Consulting   │ │ Executive    │
        └──────────────┘ └──────────────┘ └──────────────┘
```

---

# AI Agent Workflow

BI-Agent ใช้ **Multi-Agent Architecture**

```
            Data
             │
             ▼

       ┌─────────────┐
       │ ETL Agent   │
       │ Data Clean  │
       └─────┬───────┘
             │
             ▼

       ┌─────────────┐
       │ Insight     │
       │ Agent       │
       │ AI Analysis │
       └─────┬───────┘
             │
             ▼

       ┌─────────────┐
       │ Consulting  │
       │ Agent       │
       │ SCR Model   │
       └─────┬───────┘
             │
             ▼

       ┌─────────────┐
       │ Design      │
       │ Agent       │
       │ Report UX   │
       └─────┬───────┘
             │
             ▼

         Final Output
```

---

# BI Data Pipeline

```
      CSV Upload / SQL Agent
                │
                ▼
         Data Ingestion
                │
                ▼
         ETL Processing
                │
                ▼
        Data Quality Score
                │
                ▼
         AI Insight Engine
                │
                ▼
       Business Recommendations
                │
                ▼
           Report Builder
```

---

# Tech Stack

Backend

```
Python
FastAPI
Pandas
SQLAlchemy
```

AI

```
Gemini
Claude
Ollama
```

Frontend

```
Streamlit
Plotly
```

Report Engine

```
pptxgenjs
WeasyPrint
```

Deployment

```
Docker
Railway
Render
```

---

# Technology Documentation

FastAPI
[https://fastapi.tiangolo.com](https://fastapi.tiangolo.com)

Pandas
[https://pandas.pydata.org/docs/](https://pandas.pydata.org/docs/)

Ollama
[https://ollama.com](https://ollama.com)

Gemini
[https://ai.google.dev](https://ai.google.dev)

Docker
[https://docs.docker.com](https://docs.docker.com)

Streamlit
[https://streamlit.io](https://streamlit.io)

Plotly
[https://plotly.com/python/](https://plotly.com/python/)

WeasyPrint
[https://weasyprint.org](https://weasyprint.org)

---

# Project Structure

```
bi-agent/

routers/
    ingest.py
    pipeline.py
    analyze.py
    export.py

agents/
    executive_agent.py
    design_agent.py

ui/
    dashboard.py

reports/
    report_builder.py

agent/
    connector.py
    config.yaml

frontend/
    dynamic_slide_builder.js

.env
requirements.txt
README.md
```

---

# Quick Start

Clone repository

```
git clone https://github.com/yourusername/bi-agent
cd bi-agent
```

Install dependencies

```
pip install -r requirements.txt
```

Run API

```
uvicorn main:app --reload
```

Run Dashboard

```
streamlit run dashboard.py
```

---

# Example Output

Dashboard

```
• KPI cards
• Trend charts
• anomaly detection
• recommendations
```

PowerPoint

```
• 9-slide consulting deck
• SCR story structure
• insight highlights
```

PDF

```
• executive summary
• data insights
• strategic roadmap
```

---

# Portfolio Impact

This project demonstrates skills in

```
AI Engineering
Data Engineering
Business Intelligence
Multi-Agent Systems
Automation Pipelines
```

Suitable roles

```
AI Engineer
Data Engineer
Machine Learning Engineer
Analytics Engineer
AI Startup Engineer
```

---

# Author

Data Science & Business Analytics
Data Engineering Track

Focus

```
AI Systems
Data Platforms
Automation Pipelines
Business Intelligence
```

---

# Roadmap

Completed

```
CSV ingestion
ETL pipeline
AI insight engine
consulting analysis
design agent
dashboard
PPTX export
```

In Progress

```
dynamic slide generator
PDF dynamic layout
```

Upcoming

```
SQL auto pipeline
Docker data agent
scheduled ingestion
production deployment
```

---
