"""Minimal FastAPI proxy for a deployed A2A agent (Agent Runtime, agents-cli 1.1.0+).

The browser talks ONLY to this proxy (same origin, no CORS, no GCP creds in the
browser). The proxy authenticates with Application Default Credentials and
forwards chat to the deployed agent over the A2A protocol, returning replies as
structured parts the chat UI knows how to show:

  * {"kind": "text", "text": ...}  -> a normal chat bubble
  * {"kind": "a2ui", "data": ...}  -> one A2UI message (beginRendering /
    surfaceUpdate); static/index.html renders these as a card.

Why A2A: agents-cli 1.1.0 (GA) deploys ADK agents to Agent Runtime as A2A agents
and no longer registers the reasoning-engine operation schema the old
`agent_engines.get(...).stream_query()` path relied on (operation_schemas() comes
back empty). The container serves the A2A protocol over the Agent Engine HTTP
passthrough, so this proxy fetches the agent's card and sends messages with the
a2a-sdk client (the same path `agents-cli run --mode a2a` uses). This works for
both A2A and plain ADK 1.1.0 deployments (the container serves A2A either way).

Run:
  pip install -r requirements.txt
  export AGENT_ENGINE_RESOURCE_NAME="projects/.../locations/.../reasoningEngines/..."
  export AGENT_DIRECTORY="app"   # your agent's app directory (agents-cli-manifest.yaml)
  python main.py                 # -> http://localhost:8080
"""

import os
import uuid

import google.auth
import google.auth.transport.requests
import httpx
from a2a.client import ClientConfig, ClientFactory
from a2a.types import (
    AgentCard,
    FilePart,
    Message,
    Part,
    Role,
    TaskArtifactUpdateEvent,
    TextPart,
    TransportProtocol,
)
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

RESOURCE = os.environ["AGENT_ENGINE_RESOURCE_NAME"]
# The agent's app directory (matches agent_directory in agents-cli-manifest.yaml).
AGENT_DIRECTORY = os.environ.get("AGENT_DIRECTORY", "app")
# Location is embedded in the resource name: projects/<p>/locations/<loc>/reasoningEngines/<id>.
LOCATION = RESOURCE.split("/locations/")[1].split("/")[0]

# A2A endpoint for an Agent Runtime deployment, via the Agent Engine HTTP
# passthrough. The card lives at the well-known path under this base.
A2A_BASE = (
    f"https://{LOCATION}-aiplatform.googleapis.com/reasoningEngines/v1/"
    f"{RESOURCE}/api/a2a/{AGENT_DIRECTORY}"
)
A2A_CARD_URL = f"{A2A_BASE}/.well-known/agent-card.json"

# The agent tags its A2UI data parts with this mime type.
_A2UI_MIME = "application/json+a2ui"

# One set of ADC credentials, refreshed per request (access tokens expire ~1h).
_creds, _ = google.auth.default(
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)


def _auth_headers() -> dict[str, str]:
    _creds.refresh(google.auth.transport.requests.Request())
    return {
        "Authorization": f"Bearer {_creds.token}",
        "Content-Type": "application/json",
    }


app = FastAPI()


@app.exception_handler(Exception)
async def _json_errors(request: Request, exc: Exception):
    # Always return JSON so the browser never receives a plain-text 500 page
    # (which shows up in the chat as "Unexpected token 'I', "Internal S"... is
    # not valid JSON"). Any server-side failure now surfaces as a readable
    # message in the chat bubble instead.
    return JSONResponse(
        status_code=200,
        content={
            "parts": [{"kind": "text", "text": f"Error: {type(exc).__name__}: {exc}"}]
        },
    )


# Reuse ONE A2A context per user so the agent remembers the conversation.
_contexts: dict[str, str] = {}
# Cache the agent card after the first fetch.
_card: AgentCard | None = None


async def _get_card(client: httpx.AsyncClient) -> AgentCard:
    global _card
    if _card is None:
        resp = await client.get(A2A_CARD_URL)
        resp.raise_for_status()
        card = AgentCard(**resp.json())
        # Agent Runtime does not serve a public card URL, so point the client at
        # the passthrough base for message sends.
        card.url = A2A_BASE
        _card = card
    return _card


def _extract_parts(parts: list) -> list[dict]:
    """Turn A2A response parts into structured parts for the chat UI.

    Text parts pass through as {"kind": "text"}. A2UI data parts (tagged
    application/json+a2ui) become {"kind": "a2ui", "data": <message>} so the UI
    renders the card; each data part is one A2UI message (beginRendering or
    surfaceUpdate).
    """
    out: list[dict] = []
    for p in parts:
        root = getattr(p, "root", p)
        if isinstance(root, TextPart) and getattr(root, "text", None):
            out.append({"kind": "text", "text": root.text})
        elif getattr(root, "data", None) is not None:
            meta = getattr(root, "metadata", None) or {}
            mime = meta.get("mimeType") if isinstance(meta, dict) else None
            if mime == _A2UI_MIME:
                out.append({"kind": "a2ui", "data": root.data})
        elif isinstance(root, FilePart):
            uri = getattr(getattr(root, "file", None), "uri", None)
            if uri:
                out.append({"kind": "text", "text": uri})
    return out


@app.post("/chat")
async def chat(req: Request):
    body = await req.json()
    message = body.get("message", "")
    user_id = body.get("user_id") or "web-user"
    parts: list[dict] = []

    async with httpx.AsyncClient(headers=_auth_headers(), timeout=120) as client:
        card = await _get_card(client)
        factory = ClientFactory(
            ClientConfig(
                supported_transports=[
                    TransportProtocol.jsonrpc,
                    TransportProtocol.http_json,
                ],
                httpx_client=client,
            )
        )
        a2a_client = factory.create(card)

        msg = Message(
            message_id=str(uuid.uuid4()),
            role=Role.user,
            parts=[Part(root=TextPart(text=message))],
            context_id=_contexts.get(user_id),
        )

        last_task = None
        got_artifact_update = False
        async for event in a2a_client.send_message(msg):
            if not isinstance(event, tuple):
                continue
            task, update = event
            if task is not None:
                last_task = task
                if getattr(task, "context_id", None):
                    _contexts[user_id] = task.context_id
            if isinstance(update, TaskArtifactUpdateEvent):
                got_artifact_update = True
                parts.extend(_extract_parts(update.artifact.parts))

        # Non-streaming fallback: pull parts from the final task's artifacts.
        if not got_artifact_update and last_task is not None:
            for artifact in getattr(last_task, "artifacts", None) or []:
                parts.extend(_extract_parts(artifact.parts))

    if not parts:
        # The turn produced no text or UI (e.g. the agent only ran tools, or a
        # tool stalled). Be honest rather than silent.
        parts = [{"kind": "text", "text": "(The agent didn't return a reply.)"}]
    return JSONResponse({"parts": parts})


from fastapi.responses import HTMLResponse
from google.cloud import firestore
from google.cloud.firestore import FieldFilter

PROJECT_ID = "qwiklabs-gcp-03-2052da07f961"


def _get_db():
    return firestore.Client(project=PROJECT_ID)


@app.get("/dashboard/activities", response_class=HTMLResponse)
async def dashboard_activities():
    try:
        db = _get_db()
        docs = db.collection("evening_activities").where(filter=FieldFilter("child_name", "==", "Leo")).stream()
        items = []
        for doc in docs:
            d = doc.to_dict()
            status = "✅ Completed" if d.get("completed") else "⏳ Pending"
            items.append(f"""
            <div style="padding: 10px; margin: 8px 0; background: #f8fafc; border-left: 4px solid #2563eb; border-radius: 6px;">
                <div style="font-weight: bold; color: #1e293b;">{d.get('title')}</div>
                <div style="font-size: 0.85rem; color: #64748b;">Due: {d.get('due_time')} | Category: {d.get('category')} | Points: {d.get('points')}</div>
                <div style="margin-top: 4px; font-size: 0.85rem; font-weight: 600;">{status}</div>
            </div>
            """)
        content = "".join(items) if items else "<p style='color:#64748b;'>No activities assigned yet.</p>"
    except Exception as e:
        content = f"<p style='color:#ef4444;'>Error loading activities: {e}</p>"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: system-ui, sans-serif; margin: 0; padding: 12px; background: #ffffff; color: #1e293b; }}
            h3 {{ margin-top: 0; color: #2563eb; font-size: 1.05rem; display: flex; align-items: center; gap: 6px; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; }}
        </style>
    </head>
    <body>
        <h3>📋 Today's Post-School Activities</h3>
        {content}
    </body>
    </html>
    """


@app.get("/dashboard/health", response_class=HTMLResponse)
async def dashboard_health():
    try:
        db = _get_db()
        docs = db.collection("medical_records").where(filter=FieldFilter("child_name", "==", "Leo")).stream()
        items = []
        for doc in docs:
            d = doc.to_dict()
            items.append(f"""
            <div style="padding: 10px; margin: 8px 0; background: #fef2f2; border-left: 4px solid #ef4444; border-radius: 6px;">
                <div style="font-weight: bold; color: #991b1b;">[{d.get('type', '').upper()}] {d.get('title')}</div>
                <div style="font-size: 0.85rem; color: #7f1d1d;">Doctor: {d.get('doctor_name')} | Date: {d.get('date')}</div>
                <div style="font-size: 0.85rem; color: #b91c1c; font-weight: 600; margin-top: 4px;">🩺 Next Follow-up: {d.get('followup_date')}</div>
                <div style="font-size: 0.8rem; color: #450a0a; margin-top: 2px;">{d.get('notes')}</div>
            </div>
            """)
        content = "".join(items) if items else "<p style='color:#64748b;'>No medical records found.</p>"
    except Exception as e:
        content = f"<p style='color:#ef4444;'>Error loading health records: {e}</p>"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: system-ui, sans-serif; margin: 0; padding: 12px; background: #ffffff; color: #1e293b; }}
            h3 {{ margin-top: 0; color: #dc2626; font-size: 1.05rem; display: flex; align-items: center; gap: 6px; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; }}
        </style>
    </head>
    <body>
        <h3>🏥 Health & Pediatric Follow-ups</h3>
        {content}
    </body>
    </html>
    """


@app.get("/dashboard/school", response_class=HTMLResponse)
async def dashboard_school():
    items = [
        """
        <div style="padding: 10px; margin: 8px 0; background: #f0fdf4; border-left: 4px solid #16a34a; border-radius: 6px;">
            <div style="font-weight: bold; color: #166534;">🧪 4th Grade Science Fair Project</div>
            <div style="font-size: 0.85rem; color: #15803d;">Mrs. Davis - Cordos Elementary</div>
            <div style="font-size: 0.8rem; color: #166534; margin-top: 4px;">Proposals due Friday Oct 15th. Recommended topic: Solar system vs plant photosynthesis.</div>
        </div>
        """,
        """
        <div style="padding: 10px; margin: 8px 0; background: #eff6ff; border-left: 4px solid #3b82f6; border-radius: 6px;">
            <div style="font-weight: bold; color: #1e40af;">📚 Math Worksheet #12 & Chapter 4 Reading</div>
            <div style="font-size: 0.85rem; color: #1d4ed8;">Mrs. Davis - Cordos Elementary</div>
            <div style="font-size: 0.8rem; color: #1e3a8a; margin-top: 4px;">Complete 15 double-digit multiplication problems & 20 mins reading before 8 PM.</div>
        </div>
        """
    ]
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: system-ui, sans-serif; margin: 0; padding: 12px; background: #ffffff; color: #1e293b; }}
            h3 {{ margin-top: 0; color: #16a34a; font-size: 1.05rem; display: flex; align-items: center; gap: 6px; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; }}
        </style>
    </head>
    <body>
        <h3>🏫 Upcoming School & Classwork</h3>
        {"".join(items)}
    </body>
    </html>
    """


@app.get("/dashboard/announcements", response_class=HTMLResponse)
async def dashboard_announcements():
    try:
        db = _get_db()
        docs = db.collection("school_announcements").limit(5).stream()
        items = []
        for doc in docs:
            d = doc.to_dict()
            badge = "🚨 URGENT" if d.get("priority") == "urgent" else "ℹ️ NOTICE"
            color = "#dc2626" if d.get("priority") == "urgent" else "#0284c7"
            bg = "#fef2f2" if d.get("priority") == "urgent" else "#f0f9ff"
            items.append(f"""
            <div style="padding: 10px; margin: 8px 0; background: {bg}; border-left: 4px solid {color}; border-radius: 6px;">
                <div style="font-weight: bold; color: {color};">{badge}: {d.get('title')}</div>
                <div style="font-size: 0.85rem; color: #334155;">Source: {d.get('source')} | Date: {d.get('date')}</div>
                <div style="font-size: 0.8rem; color: #1e293b; margin-top: 4px;">{d.get('content')}</div>
            </div>
            """)
        content = "".join(items) if items else "<p style='color:#64748b;'>No recent announcements.</p>"
    except Exception as e:
        content = f"<p style='color:#ef4444;'>Error loading announcements: {e}</p>"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: system-ui, sans-serif; margin: 0; padding: 12px; background: #ffffff; color: #1e293b; }}
            h3 {{ margin-top: 0; color: #0284c7; font-size: 1.05rem; display: flex; align-items: center; gap: 6px; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; }}
        </style>
    </head>
    <body>
        <h3>🔔 Important Notifications</h3>
        {content}
    </body>
    </html>
    """


@app.get("/dashboard/scorecard", response_class=HTMLResponse)
async def dashboard_scorecard():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body { font-family: system-ui, sans-serif; margin: 0; padding: 10px; background: #ffffff; color: #1e293b; }
            h3 { margin: 0 0 6px 0; color: #7c3aed; font-size: 1.05rem; display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; }
            .badge { background: #f3e8ff; color: #7c3aed; font-size: 0.75rem; padding: 2px 8px; border-radius: 12px; font-weight: 700; }
            .chart-container { position: relative; width: 100%; height: 260px; }
            .stats-row { display: flex; justify-content: space-around; margin-top: 8px; background: #f8fafc; padding: 6px; border-radius: 8px; border: 1px solid #e2e8f0; font-size: 0.8rem; font-weight: 600; text-align: center; }
            .stat-val { color: #7c3aed; font-size: 0.95rem; font-weight: 800; }
        </style>
    </head>
    <body>
        <h3>
            <span>📊 Academic Scorecard Progression</span>
            <span class="badge">Grade 2 → Grade 4 (Current)</span>
        </h3>
        <div class="stats-row">
            <div>Grade 2 (2024)<br><span class="stat-val">82.3%</span></div>
            <div>Grade 3 (2025)<br><span class="stat-val">88.3%</span></div>
            <div>Grade 4 (Current)<br><span class="stat-val" style="color:#059669;">94.3% ⭐</span></div>
        </div>
        <div class="chart-container">
            <canvas id="scoreChart"></canvas>
        </div>
        <script>
            const ctx = document.getElementById('scoreChart').getContext('2d');
            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: ['Grade 2 (2024)', 'Grade 3 (2025)', 'Grade 4 (Current)'],
                    datasets: [
                        {
                            label: 'Math (%)',
                            data: [82, 88, 95],
                            backgroundColor: '#2563eb'
                        },
                        {
                            label: 'Science (%)',
                            data: [85, 91, 96],
                            backgroundColor: '#059669'
                        },
                        {
                            label: 'Reading & Language (%)',
                            data: [80, 86, 92],
                            backgroundColor: '#4f46e5'
                        },
                        {
                            label: 'Overall GPA (%)',
                            data: [82.3, 88.3, 94.3],
                            type: 'line',
                            borderColor: '#d97706',
                            borderWidth: 3,
                            fill: false,
                            tension: 0.3
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { min: 70, max: 100, ticks: { stepSize: 5 } }
                    },
                    plugins: {
                        legend: { position: 'top', labels: { boxWidth: 12, font: { size: 10 } } }
                    }
                }
            });
        </script>
    </body>
    </html>
    """


STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")



if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
