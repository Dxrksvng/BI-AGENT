"""
services/notifier.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Email + Slack Notification Service

Sends notifications when:
1. Analysis completes — immediate notification with key insights
2. Daily 08:00 AM report — PPTX attached via email

Setup (.env):
  SMTP_HOST=smtp.gmail.com
  SMTP_PORT=587
  SMTP_USER=your@gmail.com
  SMTP_PASSWORD=your_app_password      ← Gmail App Password (not real password)
  NOTIFY_EMAIL=recipient@company.com

  SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx/yyy/zzz
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os
import smtplib
import json
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText
from email.mime.base      import MIMEBase
from email                import encoders
from datetime             import datetime
from pathlib              import Path
from dotenv               import load_dotenv

load_dotenv()

# ─── Config ───────────────────────────────────────────────────────────────────
SMTP_HOST        = os.getenv("SMTP_HOST",        "smtp.gmail.com")
SMTP_PORT        = int(os.getenv("SMTP_PORT",    "587"))
SMTP_USER        = os.getenv("SMTP_USER",        "")
SMTP_PASSWORD    = os.getenv("SMTP_PASSWORD",    "")
NOTIFY_EMAIL     = os.getenv("NOTIFY_EMAIL",     SMTP_USER)
SLACK_WEBHOOK    = os.getenv("SLACK_WEBHOOK_URL","")

EMAIL_ENABLED    = bool(SMTP_USER and SMTP_PASSWORD)
SLACK_ENABLED    = bool(SLACK_WEBHOOK)


# ─── Email HTML Template ──────────────────────────────────────────────────────

def _build_email_html(
    company_name: str,
    quality_score: int,
    insights: list,
    recommendations: list,
    anomalies: list,
    pptx_attached: bool = False,
) -> str:
    now      = datetime.now().strftime("%d %B %Y, %H:%M")
    qs_color = "#10B981" if quality_score >= 80 else "#F59E0B" if quality_score >= 50 else "#EF4444"

    insights_html = "".join(
        f'<li style="padding:8px 0;border-bottom:1px solid #1E293B;color:#94A3B8;">{i}</li>'
        for i in (insights or [])[:3]
    )
    recs_html = "".join(
        f'<li style="padding:8px 0;border-bottom:1px solid #1E293B;color:#94A3B8;">'
        f'<span style="color:#22D3EE;margin-right:8px;">→</span>{r}</li>'
        for r in (recommendations or [])[:3]
    )
    anomaly_html = ""
    real_anomalies = [a for a in (anomalies or []) if "no anomal" not in a.lower()]
    if real_anomalies:
        items = "".join(
            f'<li style="padding:8px 0;border-bottom:1px solid #1E293B;color:#FCA5A5;">'
            f'<span style="color:#EF4444;margin-right:8px;">⚠</span>{a}</li>'
            for a in real_anomalies[:2]
        )
        anomaly_html = f"""
        <h3 style="color:#EF4444;font-size:13px;letter-spacing:0.08em;text-transform:uppercase;margin:24px 0 12px;">
          Risk Flags
        </h3>
        <ul style="list-style:none;padding:0;margin:0;">{items}</ul>
        """

    pptx_note = """
        <div style="background:#0F172A;border:1px solid #22D3EE;border-radius:6px;padding:16px;margin-top:24px;">
          <p style="color:#22D3EE;font-size:13px;margin:0;">
            📊 9-slide consulting deck attached to this email.
          </p>
        </div>
    """ if pptx_attached else ""

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="background:#080B14;margin:0;padding:0;font-family:'Helvetica Neue',Arial,sans-serif;">
  <div style="max-width:600px;margin:40px auto;background:#0D1117;border:1px solid #1E293B;border-radius:8px;overflow:hidden;">

    <!-- Header -->
    <div style="background:#080B14;padding:24px 32px;border-bottom:1px solid #1E293B;display:flex;align-items:center;">
      <div style="width:8px;height:8px;background:#C9A84C;border-radius:50%;margin-right:12px;"></div>
      <span style="color:#F2EDE6;font-size:18px;font-weight:500;">BI Agent</span>
      <span style="color:#334155;font-size:13px;margin-left:auto;">{now}</span>
    </div>

    <!-- Body -->
    <div style="padding:32px;">

      <h1 style="color:#F2EDE6;font-size:24px;font-weight:400;margin:0 0 6px;line-height:1.2;">
        {company_name}
      </h1>
      <p style="color:#475569;font-size:14px;margin:0 0 28px;">
        AI Analysis Complete — Business Intelligence Report
      </p>

      <!-- Quality Score -->
      <div style="background:#0F172A;border:1px solid #1E293B;border-radius:6px;padding:20px;margin-bottom:24px;display:flex;align-items:center;gap:16px;">
        <div style="font-size:42px;font-weight:700;color:{qs_color};line-height:1;">{quality_score}</div>
        <div>
          <div style="color:#F2EDE6;font-size:14px;font-weight:500;">Data Quality Score</div>
          <div style="color:#475569;font-size:12px;margin-top:4px;">out of 100 — {"Excellent" if quality_score >= 80 else "Acceptable" if quality_score >= 50 else "Needs Attention"}</div>
        </div>
      </div>

      <!-- Key Insights -->
      <h3 style="color:#C9A84C;font-size:13px;letter-spacing:0.08em;text-transform:uppercase;margin:0 0 12px;">
        Key Insights
      </h3>
      <ul style="list-style:none;padding:0;margin:0 0 24px;">
        {insights_html}
      </ul>

      <!-- Recommendations -->
      <h3 style="color:#C9A84C;font-size:13px;letter-spacing:0.08em;text-transform:uppercase;margin:0 0 12px;">
        Strategic Recommendations
      </h3>
      <ul style="list-style:none;padding:0;margin:0 0 24px;">
        {recs_html}
      </ul>

      {anomaly_html}
      {pptx_note}

      <!-- CTA -->
      <div style="text-align:center;margin-top:32px;">
        <a href="http://localhost:8501" style="background:#C9A84C;color:#080B14;padding:12px 28px;border-radius:4px;text-decoration:none;font-size:14px;font-weight:500;">
          View Full Dashboard →
        </a>
      </div>

    </div>

    <!-- Footer -->
    <div style="background:#080B14;padding:16px 32px;border-top:1px solid #1E293B;text-align:center;">
      <p style="color:#334155;font-size:11px;margin:0;">
        Generated by BI Agent · AI-Powered Business Intelligence · Confidential
      </p>
    </div>

  </div>
</body>
</html>
"""


# ─── Email Sender ─────────────────────────────────────────────────────────────

def send_email(
    subject: str,
    html_body: str,
    to_email: str = None,
    attachment_path: str = None,
) -> bool:
    if not EMAIL_ENABLED:
        print("[notifier] Email not configured — skipping")
        return False

    to = to_email or NOTIFY_EMAIL
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"BI Agent <{SMTP_USER}>"
        msg["To"]      = to

        msg.attach(MIMEText(html_body, "html"))

        # Attach PPTX if provided
        if attachment_path and Path(attachment_path).exists():
            with open(attachment_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
                encoders.encode_base64(part)
                fname = Path(attachment_path).name
                part.add_header("Content-Disposition", f'attachment; filename="{fname}"')
                msg.attach(part)

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to, msg.as_string())

        print(f"[notifier] Email sent to {to}")
        return True

    except Exception as e:
        print(f"[notifier] Email failed: {e}")
        return False


# ─── Slack Sender ─────────────────────────────────────────────────────────────

def send_slack(
    company_name: str,
    quality_score: int,
    insights: list,
    recommendations: list,
    anomalies: list,
) -> bool:
    if not SLACK_ENABLED:
        print("[notifier] Slack not configured — skipping")
        return False

    qs_color  = "#10B981" if quality_score >= 80 else "#F59E0B" if quality_score >= 50 else "#EF4444"
    qs_emoji  = "✅" if quality_score >= 80 else "⚠️" if quality_score >= 50 else "❌"
    real_anomalies = [a for a in (anomalies or []) if "no anomal" not in a.lower()]

    insight_text = "\n".join(f"• {i}" for i in (insights or [])[:3])
    rec_text     = "\n".join(f"→ {r}" for r in (recommendations or [])[:3])
    anomaly_text = "\n".join(f"⚠ {a}" for a in real_anomalies[:2]) if real_anomalies else "No anomalies detected"

    payload = {
        "text": f"*BI Agent — {company_name} Analysis Complete*",
        "attachments": [
            {
                "color": qs_color,
                "blocks": [
                    {
                        "type": "header",
                        "text": {"type": "plain_text", "text": f"📊 {company_name} — BI Report Ready"},
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Data Quality*\n{qs_emoji} {quality_score}/100"},
                            {"type": "mrkdwn", "text": f"*Generated*\n{datetime.now().strftime('%d %b %Y %H:%M')}"},
                        ],
                    },
                    {"type": "divider"},
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"*Key Insights*\n{insight_text}"},
                    },
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"*Recommendations*\n{rec_text}"},
                    },
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"*Risk Flags*\n{anomaly_text}"},
                    },
                    {"type": "divider"},
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "View Dashboard"},
                                "url":  "http://localhost:8501",
                                "style": "primary",
                            },
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "API Docs"},
                                "url":  "http://localhost:8000/docs",
                            },
                        ],
                    },
                ],
            }
        ],
    }

    try:
        resp = requests.post(SLACK_WEBHOOK, json=payload, timeout=10)
        resp.raise_for_status()
        print("[notifier] Slack notification sent")
        return True
    except Exception as e:
        print(f"[notifier] Slack failed: {e}")
        return False


# ─── Main Public API ──────────────────────────────────────────────────────────

def notify_analysis_complete(
    company_name: str,
    analysis: dict,
    report: dict,
    pptx_path: str = None,
    to_email: str  = None,
):
    """
    Send Email + Slack notification when analysis completes.
    Call this from export.py after PPTX is generated.

    Usage:
        from services.notifier import notify_analysis_complete
        notify_analysis_complete(
            company_name = "Acme Corp",
            analysis     = analysis_dict,
            report       = report_dict,
            pptx_path    = "/tmp/deck.pptx",
        )
    """
    if hasattr(analysis, "dict"): analysis = analysis.dict()
    if hasattr(report,   "dict"): report   = report.dict()

    qs              = report.get("quality_score", 0) if isinstance(report, dict) else 0
    insights        = analysis.get("key_insights",    []) if isinstance(analysis, dict) else []
    recommendations = analysis.get("recommendations", []) if isinstance(analysis, dict) else []
    anomalies       = analysis.get("anomalies",       []) if isinstance(analysis, dict) else []

    subject = f"BI Agent — {company_name} Analysis Ready ({datetime.now().strftime('%d %b %Y')})"

    # Email
    html = _build_email_html(
        company_name     = company_name,
        quality_score    = qs,
        insights         = insights,
        recommendations  = recommendations,
        anomalies        = anomalies,
        pptx_attached    = bool(pptx_path),
    )
    send_email(subject, html, to_email=to_email, attachment_path=pptx_path)

    # Slack
    send_slack(company_name, qs, insights, recommendations, anomalies)


def notify_daily_report(
    company_name: str,
    analysis: dict,
    report: dict,
    pptx_path: str = None,
):
    """
    Send daily scheduled report at 08:00 AM.
    Called by auto_pipeline.py scheduler.
    """
    subject = f"[Daily Report] {company_name} — {datetime.now().strftime('%d %b %Y')}"
    notify_analysis_complete(company_name, analysis, report, pptx_path)
    print(f"[notifier] Daily report sent for {company_name}")
