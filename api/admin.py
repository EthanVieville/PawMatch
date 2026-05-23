import json
import os
import logging
from datetime import datetime, timezone
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

    # Totaux globaux
    total_row = db.execute(text("""
        SELECT
            COUNT(*)                                                        AS calls,
            COALESCE(SUM(cost_usd), 0)                                      AS cost_usd,
            COALESCE(SUM(input_tokens), 0)                                  AS input_tokens,
            COALESCE(SUM(output_tokens), 0)                                 AS output_tokens,
            COALESCE(AVG(latency_ms), 0)                                    AS avg_latency_ms,
            COALESCE(SUM(CASE WHEN error THEN 1 ELSE 0 END), 0)             AS errors
        FROM llm_traces
    """)).fetchone()

    # Coût projeté (basé sur les 7 derniers jours → extrapolé à 30j)
    projected_row = db.execute(text("""
        SELECT COALESCE(SUM(cost_usd), 0) * (30.0 / 7) AS projected_monthly
        FROM llm_traces
        WHERE created_at >= NOW() - INTERVAL '7 days'
    """)).fetchone()

    # Percentiles de latence
    latency_row = db.execute(text("""
        SELECT
            COALESCE(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY latency_ms), 0) AS p50,
            COALESCE(PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY latency_ms), 0) AS p90,
            COALESCE(PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY latency_ms), 0) AS p99
        FROM llm_traces
        WHERE NOT error
    """)).fetchone()

    # Taux tool use (sur les appels chat uniquement)
    tool_use_row = db.execute(text("""
        SELECT
            COUNT(*)                                                                        AS total_chat,
            COUNT(CASE WHEN tool_calls IS NOT NULL
                            AND jsonb_typeof(tool_calls) = 'array'
                            AND jsonb_array_length(tool_calls) > 0 THEN 1 END)             AS with_tools
        FROM llm_traces
        WHERE feature = 'chat'
    """)).fetchone()

    # Top tools appelés (tous features)
    top_tools_rows = db.execute(text("""
        SELECT
            tool->>'name'   AS tool_name,
            COUNT(*)        AS cnt
        FROM llm_traces,
             jsonb_array_elements(tool_calls) AS tool
        WHERE tool_calls IS NOT NULL
          AND jsonb_typeof(tool_calls) = 'array'
        GROUP BY tool_name
        ORDER BY cnt DESC
        LIMIT 8
    """)).fetchall()

    # Par feature
    feat_rows = db.execute(text("""
        SELECT
            feature,
            COUNT(*)                                                        AS calls,
            COALESCE(SUM(cost_usd), 0)                                      AS cost_usd,
            COALESCE(SUM(input_tokens), 0)                                  AS input_tokens,
            COALESCE(SUM(output_tokens), 0)                                 AS output_tokens,
            COALESCE(AVG(latency_ms), 0)                                    AS avg_latency_ms,
            COALESCE(SUM(CASE WHEN error THEN 1 ELSE 0 END), 0)             AS errors
        FROM llm_traces
        GROUP BY feature
        ORDER BY cost_usd DESC
    """)).fetchall()

    # Coût journalier (30j)
    daily_rows = db.execute(text("""
        SELECT
            DATE(created_at AT TIME ZONE 'UTC')   AS day,
            COALESCE(SUM(cost_usd), 0)            AS cost_usd
        FROM llm_traces
        WHERE created_at >= NOW() - INTERVAL '30 days'
        GROUP BY day
        ORDER BY day
    """)).fetchall()

    # Statut base de données animaux
    db_status_row = db.execute(text("""
        SELECT
            COUNT(*)                        AS total,
            COUNT(description_rewritten)    AS rewritten,
            COUNT(embedding)                AS with_embedding
        FROM animals
    """)).fetchone()

    # 100 dernières traces
    trace_rows = db.execute(text("""
        SELECT id, feature, model_id, input_tokens, output_tokens,
               cost_usd, latency_ms, tool_calls, rag_chunks_used, error, created_at
        FROM llm_traces
        ORDER BY created_at DESC
        LIMIT 100
    """)).fetchall()

    tool_use_rate = 0.0
    if tool_use_row.total_chat:
        tool_use_rate = round(tool_use_row.with_tools / tool_use_row.total_chat * 100, 1)

    return {
        "total": {
            "calls":             int(total_row.calls),
            "cost_usd":          float(total_row.cost_usd),
            "input_tokens":      int(total_row.input_tokens),
            "output_tokens":     int(total_row.output_tokens),
            "avg_latency_ms":    float(total_row.avg_latency_ms),
            "errors":            int(total_row.errors),
            "projected_monthly": float(projected_row.projected_monthly),
            "p50":               float(latency_row.p50),
            "p90":               float(latency_row.p90),
            "p99":               float(latency_row.p99),
            "tool_use_rate":     tool_use_rate,
        },
        "top_tools": [
            {"name": r.tool_name, "count": int(r.cnt)}
            for r in top_tools_rows
        ],
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
        "db_status": {
            "total":          int(db_status_row.total),
            "rewritten":      int(db_status_row.rewritten),
            "with_embedding": int(db_status_row.with_embedding),
        },
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
    body { background: #f0f2f5; font-family: system-ui, sans-serif; }
    .kpi-card  { border-top: 4px solid; border-radius: .5rem; }
    .kpi-cost    { border-color: #dc3545; }
    .kpi-calls   { border-color: #0d6efd; }
    .kpi-latency { border-color: #198754; }
    .kpi-errors  { border-color: #fd7e14; }
    .kpi-value { font-size: 1.9rem; font-weight: 700; line-height: 1.15; }
    .kpi-label { font-size: .72rem; text-transform: uppercase; letter-spacing: .06em; color: #6c757d; }
    .kpi-sub   { font-size: .78rem; color: #6c757d; margin-top: .2rem; }
    .kpi-sub b { color: #343a40; }
    .section-title { font-size: .82rem; font-weight: 700; text-transform: uppercase;
                     letter-spacing: .07em; color: #6c757d; margin-bottom: .8rem; }
    .table th { font-size: .76rem; text-transform: uppercase; letter-spacing: .04em; color: #6c757d; }
    .table td { font-size: .84rem; vertical-align: middle; }
    .progress  { border-radius: 99px; }
    .proj-badge { font-size: .72rem; background: #fff3cd; color: #856404;
                  border-radius: 4px; padding: 1px 6px; margin-left: 4px; }
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

  <!-- ── KPIs ── -->
  <div class="row g-3 mb-4">

    <div class="col-6 col-md-3">
      <div class="card kpi-card kpi-cost h-100 p-3">
        <div class="kpi-label">Cout total</div>
        <div class="kpi-value text-danger">__KPI_COST__</div>
        <div class="kpi-sub"><b>__KPI_TOKENS__</b> tokens au total</div>
        <div class="kpi-sub mt-1">
          Projete/mois&nbsp;<span class="proj-badge">__KPI_PROJECTED__</span>
        </div>
      </div>
    </div>

    <div class="col-6 col-md-3">
      <div class="card kpi-card kpi-calls h-100 p-3">
        <div class="kpi-label">Appels LLM</div>
        <div class="kpi-value text-primary">__KPI_CALLS__</div>
        <div class="kpi-sub"><b>__KPI_IN__</b> in / <b>__KPI_OUT__</b> out</div>
        <div class="kpi-sub mt-1">Tool use : <b>__KPI_TOOL_RATE__%</b> des chats</div>
      </div>
    </div>

    <div class="col-6 col-md-3">
      <div class="card kpi-card kpi-latency h-100 p-3">
        <div class="kpi-label">Latence</div>
        <div class="kpi-value text-success">__KPI_LATENCY__ ms</div>
        <div class="kpi-sub">Moyenne &middot; <b>p50 __KPI_P50__ ms</b></div>
        <div class="kpi-sub mt-1">p90 <b>__KPI_P90__ ms</b> &middot; p99 <b>__KPI_P99__ ms</b></div>
      </div>
    </div>

    <div class="col-6 col-md-3">
      <div class="card kpi-card kpi-errors h-100 p-3">
        <div class="kpi-label">Erreurs</div>
        <div class="kpi-value text-warning">__KPI_ERRORS__</div>
        <div class="kpi-sub"><b>__KPI_ERROR_RATE__%</b> taux d'erreur</div>
        <div class="kpi-sub mt-1">Sur __KPI_CALLS__ appels totaux</div>
      </div>
    </div>

  </div>

  <!-- ── Charts coût + features ── -->
  <div class="row g-3 mb-4">
    <div class="col-md-8">
      <div class="card h-100">
        <div class="card-body">
          <div class="section-title">Cout journalier &mdash; 30 derniers jours</div>
          <canvas id="chart-daily" height="90"></canvas>
        </div>
      </div>
    </div>
    <div class="col-md-4">
      <div class="card h-100">
        <div class="card-body d-flex flex-column">
          <div class="section-title">Repartition par feature</div>
          <div class="d-flex justify-content-center align-items-center flex-grow-1">
            <canvas id="chart-features" width="200" height="200"></canvas>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ── Statut DB + Top tools ── -->
  <div class="row g-3 mb-4">

    <div class="col-md-5">
      <div class="card h-100">
        <div class="card-body">
          <div class="section-title">Statut base de donnees</div>

          <div class="d-flex justify-content-between align-items-baseline mb-1">
            <span class="small fw-semibold">Animaux total</span>
            <span class="small text-muted">__DB_TOTAL__</span>
          </div>

          <div class="mb-3">
            <div class="d-flex justify-content-between mb-1">
              <small>Descriptions reecrites</small>
              <small><b>__DB_REWRITTEN__</b> / __DB_TOTAL__ &nbsp;(__DB_REWRITTEN_PCT__%)</small>
            </div>
            <div class="progress" style="height:8px;">
              <div class="progress-bar __DB_REWRITTEN_COLOR__" style="width:__DB_REWRITTEN_PCT__%"></div>
            </div>
          </div>

          <div class="mb-2">
            <div class="d-flex justify-content-between mb-1">
              <small>Embeddings calcules</small>
              <small><b>__DB_EMBEDDED__</b> / __DB_TOTAL__ &nbsp;(__DB_EMBEDDED_PCT__%)</small>
            </div>
            <div class="progress" style="height:8px;">
              <div class="progress-bar __DB_EMBEDDED_COLOR__" style="width:__DB_EMBEDDED_PCT__%"></div>
            </div>
          </div>

          <hr class="my-3">
          <div class="small text-muted">
            <span class="me-3">&#128464; <b>__DB_REWRITTEN__</b> fiches avec description LLM</span><br>
            <span>&#128200; <b>__DB_NOT_REWRITTEN__</b> fiches restantes a traiter</span>
          </div>
        </div>
      </div>
    </div>

    <div class="col-md-7">
      <div class="card h-100">
        <div class="card-body">
          <div class="section-title">Top tools appeles par le LLM</div>
          <canvas id="chart-tools" height="__CHART_TOOLS_HEIGHT__"></canvas>
        </div>
      </div>
    </div>

  </div>

  <!-- ── Feature breakdown ── -->
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

  <!-- ── Traces recentes ── -->
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
const DAILY       = __DAILY_JSON__;
const FEATS       = __FEATS_JSON__;
const TOP_TOOLS   = __TOP_TOOLS_JSON__;

// Coût journalier
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

// Feature donut
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

// Top tools (barre horizontale)
if (TOP_TOOLS.length > 0) {
  new Chart(document.getElementById('chart-tools'), {
    type: 'bar',
    data: {
      labels: TOP_TOOLS.map(t => t.name),
      datasets: [{
        label: 'Appels',
        data: TOP_TOOLS.map(t => t.count),
        backgroundColor: [
          '#0d6efd','#6f42c1','#198754','#fd7e14','#dc3545','#20c997','#0dcaf0','#6c757d'
        ],
        borderRadius: 4,
      }],
    },
    options: {
      indexAxis: 'y',
      plugins: { legend: { display: false } },
      scales: { x: { beginAtZero: true, ticks: { stepSize: 1 } } },
    },
  });
}
</script>
</body>
</html>"""


# ── Helpers de rendu ───────────────────────────────────────────────────────────

def _badge(feature: str) -> str:
    cls = "primary" if feature == "chat" else "secondary"
    return f'<span class="badge bg-{cls}">{feature}</span>'


def _pct_color(pct: float) -> str:
    if pct >= 75:
        return "bg-success"
    if pct >= 25:
        return "bg-warning"
    return "bg-danger"


def _render(stats: dict, token: str) -> str:
    t   = stats["total"]
    dbs = stats["db_status"]

    error_rate = round(t["errors"] / t["calls"] * 100, 1) if t["calls"] else 0.0

    rewritten_pct = round(dbs["rewritten"] / dbs["total"] * 100, 1) if dbs["total"] else 0.0
    embedded_pct  = round(dbs["with_embedding"] / dbs["total"] * 100, 1) if dbs["total"] else 0.0

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
        tools  = ", ".join(tc["name"] for tc in r["tool_calls"]) if r["tool_calls"] else "—"
        status = ('<span class="badge bg-danger">erreur</span>'
                  if r["error"] else '<span class="badge bg-success">ok</span>')
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

    # Hauteur dynamique du chart top tools
    tools_height = max(60, len(stats["top_tools"]) * 32)

    now = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")

    html = _ADMIN_TEMPLATE
    html = html.replace("__TOKEN__",              token)
    html = html.replace("__GENERATED_AT__",       now)
    html = html.replace("__KPI_COST__",           f'${t["cost_usd"]:.5f}')
    html = html.replace("__KPI_TOKENS__",         f'{t["input_tokens"] + t["output_tokens"]:,}')
    html = html.replace("__KPI_PROJECTED__",      f'${t["projected_monthly"]:.3f}')
    html = html.replace("__KPI_CALLS__",          str(t["calls"]))
    html = html.replace("__KPI_IN__",             f'{t["input_tokens"]:,}')
    html = html.replace("__KPI_OUT__",            f'{t["output_tokens"]:,}')
    html = html.replace("__KPI_TOOL_RATE__",      str(t["tool_use_rate"]))
    html = html.replace("__KPI_LATENCY__",        f'{t["avg_latency_ms"]:.0f}')
    html = html.replace("__KPI_P50__",            f'{t["p50"]:.0f}')
    html = html.replace("__KPI_P90__",            f'{t["p90"]:.0f}')
    html = html.replace("__KPI_P99__",            f'{t["p99"]:.0f}')
    html = html.replace("__KPI_ERRORS__",         str(t["errors"]))
    html = html.replace("__KPI_ERROR_RATE__",     str(error_rate))
    html = html.replace("__DB_TOTAL__",           f'{dbs["total"]:,}')
    html = html.replace("__DB_REWRITTEN__",       f'{dbs["rewritten"]:,}')
    html = html.replace("__DB_REWRITTEN_PCT__",   str(rewritten_pct))
    html = html.replace("__DB_REWRITTEN_COLOR__", _pct_color(rewritten_pct))
    html = html.replace("__DB_EMBEDDED__",        f'{dbs["with_embedding"]:,}')
    html = html.replace("__DB_EMBEDDED_PCT__",    str(embedded_pct))
    html = html.replace("__DB_EMBEDDED_COLOR__",  _pct_color(embedded_pct))
    html = html.replace("__DB_NOT_REWRITTEN__",   f'{dbs["total"] - dbs["rewritten"]:,}')
    html = html.replace("__TBODY_FEATURES__",     feat_rows)
    html = html.replace("__TBODY_TRACES__",       trace_rows)
    html = html.replace("__DAILY_JSON__",         json.dumps(stats["daily"]))
    html = html.replace("__FEATS_JSON__",         json.dumps(stats["by_feature"]))
    html = html.replace("__TOP_TOOLS_JSON__",     json.dumps(stats["top_tools"]))
    html = html.replace("__CHART_TOOLS_HEIGHT__", str(tools_height))
    return html


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/admin", response_class=HTMLResponse, include_in_schema=False)
def admin_dashboard(token: str = "", db: Session = Depends(get_db)):
    _check_token(token)
    return _render(_get_stats(db), token)


@router.get("/admin/api/stats", include_in_schema=False)
def admin_stats(token: str = "", db: Session = Depends(get_db)):
    _check_token(token)
    return _get_stats(db)