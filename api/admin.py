import json
import os
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")


def _check_token(token: str) -> None:
    if not ADMIN_TOKEN or token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Token invalide")


# ── Requêtes stats ─────────────────────────────────────────────────────────────

def _get_stats(db: Session) -> dict:
    total_row = db.execute(text("""
        SELECT
            COUNT(*)                                                  AS calls,
            COALESCE(SUM(cost_usd), 0)                                AS cost_usd,
            COALESCE(SUM(input_tokens), 0)                            AS input_tokens,
            COALESCE(SUM(output_tokens), 0)                           AS output_tokens,
            COALESCE(AVG(latency_ms), 0)                              AS avg_latency_ms,
            COALESCE(SUM(CASE WHEN error THEN 1 ELSE 0 END), 0)       AS errors
        FROM llm_traces
    """)).fetchone()

    feat_rows = db.execute(text("""
        SELECT
            feature,
            COUNT(*)                                                  AS calls,
            COALESCE(SUM(cost_usd), 0)                                AS cost_usd,
            COALESCE(SUM(input_tokens), 0)                            AS input_tokens,
            COALESCE(SUM(output_tokens), 0)                           AS output_tokens,
            COALESCE(AVG(latency_ms), 0)                              AS avg_latency_ms,
            COALESCE(SUM(CASE WHEN error THEN 1 ELSE 0 END), 0)       AS errors
        FROM llm_traces
        GROUP BY feature
        ORDER BY cost_usd DESC
    """)).fetchall()

    daily_rows = db.execute(text("""
        SELECT
            DATE(created_at AT TIME ZONE 'UTC')                       AS day,
            COALESCE(SUM(cost_usd), 0)                                AS cost_usd
        FROM llm_traces
        WHERE created_at >= NOW() - INTERVAL '30 days'
        GROUP BY day
        ORDER BY day
    """)).fetchall()

    trace_rows = db.execute(text("""
        SELECT id, feature, model_id, input_tokens, output_tokens,
               cost_usd, latency_ms, tool_calls, rag_chunks_used, error, created_at
        FROM llm_traces
        ORDER BY created_at DESC
        LIMIT 100
    """)).fetchall()

    return {
        "total": {
            "calls":          int(total_row.calls),
            "cost_usd":       float(total_row.cost_usd),
            "input_tokens":   int(total_row.input_tokens),
            "output_tokens":  int(total_row.output_tokens),
            "avg_latency_ms": float(total_row.avg_latency_ms),
            "errors":         int(total_row.errors),
        },
        "by_feature": [
            {
                "feature":        r.feature,
                "calls":          int(r.calls),
                "cost_usd":       float(r.cost_usd),
                "input_tokens":   int(r.input_tokens),
                "output_tokens":  int(r.output_tokens),
                "avg_latency_ms": float(r.avg_latency_ms),
                "errors":         int(r.errors),
            }
            for r in feat_rows
        ],
        "daily": [
            {"date": str(r.day), "cost_usd": float(r.cost_usd)}
            for r in daily_rows
        ],
        "recent_traces": [
            {
                "id":              str(r.id),
                "feature":         r.feature,
                "model_id":        r.model_id,
                "input_tokens":    r.input_tokens,
                "output_tokens":   r.output_tokens,
                "cost_usd":        float(r.cost_usd),
                "latency_ms":      r.latency_ms,
                "tool_calls":      r.tool_calls,
                "rag_chunks_used": r.rag_chunks_used,
                "error":           r.error,
                "created_at":      r.created_at.isoformat() if r.created_at else None,
            }
            for r in trace_rows
        ],
    }


# ── Template HTML ──────────────────────────────────────────────────────────────

_ADMIN_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PawMatch — LLMOps</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
  <style>
    body { background: #f0f2f5; }
    .kpi-card { border-top: 4px solid; border-radius: .5rem; }
    .kpi-cost    { border-color: #dc3545; }
    .kpi-calls   { border-color: #0d6efd; }
    .kpi-latency { border-color: #198754; }
    .kpi-errors  { border-color: #fd7e14; }
    .kpi-value   { font-size: 2rem; font-weight: 700; line-height: 1.1; }
    .kpi-label   { font-size: .75rem; text-transform: uppercase; letter-spacing: .05em; color: #6c757d; }
    .kpi-sub     { font-size: .8rem; color: #6c757d; margin-top: .25rem; }
    .section-title { font-size: .85rem; font-weight: 600; text-transform: uppercase;
                     letter-spacing: .06em; color: #6c757d; margin-bottom: .75rem; }
    .table th  { font-size: .78rem; text-transform: uppercase; letter-spacing: .04em; color: #6c757d; }
    .table td  { font-size: .85rem; vertical-align: middle; }
  </style>
</head>
<body>

<nav class="navbar navbar-dark bg-dark mb-4 px-4">
  <span class="navbar-brand fw-bold">&#x1F43E; PawMatch &mdash; LLMOps</span>
  <span class="d-flex align-items-center gap-3">
    <span class="text-muted small">__GENERATED_AT__</span>
    <a href="?token=__TOKEN__" class="btn btn-outline-light btn-sm">&#x21BB; Rafraichir</a>
  </span>
</nav>

<div class="container-fluid px-4">

  <!-- KPIs -->
  <div class="row g-3 mb-4">
    <div class="col-6 col-md-3">
      <div class="card kpi-card kpi-cost h-100 p-3">
        <div class="kpi-label">Cout total</div>
        <div class="kpi-value text-danger">__KPI_COST__</div>
        <div class="kpi-sub">__KPI_TOKENS__ tokens</div>
      </div>
    </div>
    <div class="col-6 col-md-3">
      <div class="card kpi-card kpi-calls h-100 p-3">
        <div class="kpi-label">Appels LLM</div>
        <div class="kpi-value text-primary">__KPI_CALLS__</div>
        <div class="kpi-sub">__KPI_IN__ in / __KPI_OUT__ out</div>
      </div>
    </div>
    <div class="col-6 col-md-3">
      <div class="card kpi-card kpi-latency h-100 p-3">
        <div class="kpi-label">Latence moy.</div>
        <div class="kpi-value text-success">__KPI_LATENCY__ ms</div>
        <div class="kpi-sub">par appel</div>
      </div>
    </div>
    <div class="col-6 col-md-3">
      <div class="card kpi-card kpi-errors h-100 p-3">
        <div class="kpi-label">Erreurs</div>
        <div class="kpi-value text-warning">__KPI_ERRORS__</div>
        <div class="kpi-sub">__KPI_ERROR_RATE__% taux</div>
      </div>
    </div>
  </div>

  <!-- Charts -->
  <div class="row g-3 mb-4">
    <div class="col-md-8">
      <div class="card h-100">
        <div class="card-body">
          <div class="section-title">Cout journalier - 30 derniers jours</div>
          <canvas id="chart-daily" height="90"></canvas>
        </div>
      </div>
    </div>
    <div class="col-md-4">
      <div class="card h-100">
        <div class="card-body d-flex flex-column">
          <div class="section-title">Repartition par feature</div>
          <div class="d-flex justify-content-center align-items-center flex-grow-1">
            <canvas id="chart-features" width="220" height="220"></canvas>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Feature breakdown -->
  <div class="row g-3 mb-4">
    <div class="col-12">
      <div class="card">
        <div class="card-body pb-0">
          <div class="section-title">Detail par feature</div>
        </div>
        <div class="table-responsive">
          <table class="table table-sm mb-0">
            <thead class="table-light">
              <tr>
                <th>Feature</th><th>Appels</th><th>Tokens in</th><th>Tokens out</th>
                <th>Cout total</th><th>Cout / appel</th><th>Latence moy.</th><th>Erreurs</th>
              </tr>
            </thead>
            <tbody>__TBODY_FEATURES__</tbody>
          </table>
        </div>
      </div>
    </div>
  </div>

  <!-- Recent traces -->
  <div class="row g-3 mb-5">
    <div class="col-12">
      <div class="card">
        <div class="card-body pb-0">
          <div class="section-title">Dernieres 100 traces</div>
        </div>
        <div class="table-responsive">
          <table class="table table-sm table-hover mb-0">
            <thead class="table-light">
              <tr>
                <th>Date</th><th>Feature</th><th>Modele</th>
                <th>In / Out</th><th>Cout</th><th>Latence</th>
                <th>Tools</th><th>RAG</th><th>Statut</th>
              </tr>
            </thead>
            <tbody>__TBODY_TRACES__</tbody>
          </table>
        </div>
      </div>
    </div>
  </div>

</div>

<script>
const DAILY  = __DAILY_JSON__;
const FEATS  = __FEATS_JSON__;

new Chart(document.getElementById('chart-daily'), {
  type: 'line',
  data: {
    labels: DAILY.map(d => d.date),
    datasets: [{
      label: 'Cout ($)',
      data: DAILY.map(d => d.cost_usd),
      borderColor: '#dc3545',
      backgroundColor: 'rgba(220,53,69,.1)',
      fill: true, tension: 0.35, pointRadius: 3,
    }],
  },
  options: {
    plugins: { legend: { display: false } },
    scales: { y: { beginAtZero: true, ticks: { callback: v => '$' + v.toFixed(5) } } },
  },
});

const FEAT_COLORS = { chat: '#0d6efd', description_rewrite: '#6f42c1' };
new Chart(document.getElementById('chart-features'), {
  type: 'doughnut',
  data: {
    labels: FEATS.map(f => f.feature),
    datasets: [{
      data: FEATS.map(f => f.calls),
      backgroundColor: FEATS.map(f => FEAT_COLORS[f.feature] || '#6c757d'),
      borderWidth: 2,
    }],
  },
  options: { plugins: { legend: { position: 'bottom' } }, cutout: '60%' },
});
</script>
</body>
</html>"""


def _badge(feature: str) -> str:
    cls = "primary" if feature == "chat" else "secondary"
    return f'<span class="badge bg-{cls}">{feature}</span>'


def _render(stats: dict, token: str) -> str:
    from datetime import datetime, timezone

    t = stats["total"]
    error_rate = round(t["errors"] / t["calls"] * 100, 1) if t["calls"] else 0.0

    # Feature table rows
    feat_rows = ""
    for f in stats["by_feature"]:
        cpa = f["cost_usd"] / f["calls"] if f["calls"] else 0
        feat_rows += (
            f'<tr><td>{_badge(f["feature"])}</td>'
            f'<td>{f["calls"]}</td>'
            f'<td>{f["input_tokens"]:,}</td>'
            f'<td>{f["output_tokens"]:,}</td>'
            f'<td>${f["cost_usd"]:.5f}</td>'
            f'<td>${cpa:.5f}</td>'
            f'<td>{f["avg_latency_ms"]:.0f} ms</td>'
            f'<td>{f["errors"]}</td></tr>'
        )

    # Traces table rows
    trace_rows = ""
    for r in stats["recent_traces"]:
        tools = ", ".join(tc["name"] for tc in r["tool_calls"]) if r["tool_calls"] else "—"
        status = '<span class="badge bg-danger">erreur</span>' if r["error"] else '<span class="badge bg-success">ok</span>'
        dt = r["created_at"][:16].replace("T", " ") if r["created_at"] else "—"
        model_short = r["model_id"].split(".")[-1] if "." in r["model_id"] else r["model_id"]
        trace_rows += (
            f'<tr><td class="text-nowrap">{dt}</td>'
            f'<td>{_badge(r["feature"])}</td>'
            f'<td><small class="text-muted">{model_short}</small></td>'
            f'<td>{r["input_tokens"]} / {r["output_tokens"]}</td>'
            f'<td>${r["cost_usd"]:.5f}</td>'
            f'<td>{r["latency_ms"]} ms</td>'
            f'<td><small>{tools}</small></td>'
            f'<td>{r["rag_chunks_used"] or 0}</td>'
            f'<td>{status}</td></tr>'
        )

    now = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")

    html = _ADMIN_TEMPLATE
    html = html.replace("__TOKEN__",        token)
    html = html.replace("__GENERATED_AT__", now)
    html = html.replace("__KPI_COST__",     f'${t["cost_usd"]:.5f}')
    html = html.replace("__KPI_TOKENS__",   f'{t["input_tokens"] + t["output_tokens"]:,}')
    html = html.replace("__KPI_CALLS__",    str(t["calls"]))
    html = html.replace("__KPI_IN__",       f'{t["input_tokens"]:,}')
    html = html.replace("__KPI_OUT__",      f'{t["output_tokens"]:,}')
    html = html.replace("__KPI_LATENCY__",  f'{t["avg_latency_ms"]:.0f}')
    html = html.replace("__KPI_ERRORS__",   str(t["errors"]))
    html = html.replace("__KPI_ERROR_RATE__", str(error_rate))
    html = html.replace("__TBODY_FEATURES__", feat_rows)
    html = html.replace("__TBODY_TRACES__",   trace_rows)
    html = html.replace("__DAILY_JSON__",  json.dumps(stats["daily"]))
    html = html.replace("__FEATS_JSON__",  json.dumps(stats["by_feature"]))
    return html


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/admin", response_class=HTMLResponse, include_in_schema=False)
def admin_dashboard(token: str = "", db: Session = Depends(get_db)):
    _check_token(token)
    stats = _get_stats(db)
    return _render(stats, token)


@router.get("/admin/api/stats", include_in_schema=False)
def admin_stats(token: str = "", db: Session = Depends(get_db)):
    _check_token(token)
    return _get_stats(db)