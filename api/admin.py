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

    # Cache sémantique
    cache_row = db.execute(text("""
        SELECT
            COUNT(*) FILTER (WHERE expires_at > NOW())                          AS active_entries,
            COUNT(*)                                                             AS total_entries,
            COALESCE(SUM(hit_count) FILTER (WHERE expires_at > NOW()), 0)       AS active_hits
        FROM llm_cache
    """)).fetchone()

    cache_rate_row = db.execute(text("""
        SELECT
            COUNT(*) FILTER (WHERE feature = 'chat_cached')             AS cached_calls,
            COUNT(*) FILTER (WHERE feature IN ('chat', 'chat_cached'))  AS total_chat_calls,
            COALESCE(AVG(cost_usd) FILTER (WHERE feature = 'chat'), 0)  AS avg_chat_cost
        FROM llm_traces
    """)).fetchone()

    # Feedback utilisateur
    feedback_row = db.execute(text("""
        SELECT
            COUNT(*) FILTER (WHERE feedback IS NOT NULL)     AS total_feedback,
            COUNT(*) FILTER (WHERE feedback = 'positive')   AS positive,
            COUNT(*) FILTER (WHERE feedback = 'negative')   AS negative
        FROM llm_traces
        WHERE feature IN ('chat', 'quiz')
    """)).fetchone()

    # Traces avec feedback (pour l'onglet détail)
    feedback_traces = db.execute(text("""
        SELECT id, feature, created_at, feedback,
               user_message, assistant_response, tool_calls, rag_chunks_used, latency_ms
        FROM llm_traces
        WHERE feedback IS NOT NULL
          AND feature IN ('chat', 'quiz')
        ORDER BY created_at DESC
        LIMIT 200
    """)).fetchall()

    # 100 dernières traces
    trace_rows = db.execute(text("""
        SELECT id, feature, model_id, input_tokens, output_tokens,
               cost_usd, latency_ms, tool_calls, rag_chunks_used, error, feedback, created_at
        FROM llm_traces
        ORDER BY created_at DESC
        LIMIT 100
    """)).fetchall()

    tool_use_rate = 0.0
    if tool_use_row.total_chat:
        tool_use_rate = round(tool_use_row.with_tools / tool_use_row.total_chat * 100, 1)

    satisfaction_rate = 0.0
    if feedback_row.total_feedback:
        satisfaction_rate = round(feedback_row.positive / feedback_row.total_feedback * 100, 1)

    return {
        "feedback": {
            "total":             int(feedback_row.total_feedback),
            "positive":          int(feedback_row.positive),
            "negative":          int(feedback_row.negative),
            "satisfaction_rate": satisfaction_rate,
        },
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
        "cache": {
            "active_entries":  int(cache_row.active_entries),
            "total_entries":   int(cache_row.total_entries),
            "active_hits":     int(cache_row.active_hits),
            "cached_calls":    int(cache_rate_row.cached_calls),
            "total_chat_calls": int(cache_rate_row.total_chat_calls),
            "estimated_savings": float(cache_rate_row.cached_calls) * float(cache_rate_row.avg_chat_cost),
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
                "feedback":        r.feedback,
                "created_at":      r.created_at.isoformat() if r.created_at else None,
            }
            for r in trace_rows
        ],
        "feedback_traces": [
            {
                "id":               str(r.id),
                "feature":          r.feature,
                "feedback":         r.feedback,
                "user_message":     r.user_message or "",
                "assistant_response": r.assistant_response or "",
                "tool_calls":       r.tool_calls,
                "rag_chunks_used":  r.rag_chunks_used,
                "latency_ms":       r.latency_ms,
                "created_at":       r.created_at.isoformat() if r.created_at else None,
            }
            for r in feedback_traces
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
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
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
    .kpi-feedback { border-color: #20c997; }
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

  <!-- ── Onglets ── -->
  <ul class="nav nav-tabs mb-4" id="mainTabs">
    <li class="nav-item">
      <a class="nav-link active" data-bs-toggle="tab" href="#tab-overview">Vue d'ensemble</a>
    </li>
    <li class="nav-item">
      <a class="nav-link" data-bs-toggle="tab" href="#tab-feedback">
        Feedback
        <span class="badge ms-1 __BADGE_NEG_CLASS__">__KPI_FB_NEG__ &#128078;</span>
      </a>
    </li>
  </ul>

  <div class="tab-content">
  <div class="tab-pane fade show active" id="tab-overview">

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

    <div class="col-6 col-md-3">
      <div class="card kpi-card kpi-feedback h-100 p-3">
        <div class="kpi-label">Satisfaction utilisateur</div>
        <div class="kpi-value" style="color:#20c997;">__KPI_SATISFACTION__%</div>
        <div class="kpi-sub">&#128077; <b>__KPI_FB_POS__</b> &nbsp;&#128078; <b>__KPI_FB_NEG__</b></div>
        <div class="kpi-sub mt-1"><b>__KPI_FB_TOTAL__</b> réponses notées</div>
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

  <!-- ── Cache semantique ── -->
  <div class="row g-3 mb-4">
    <div class="col-12">
      <div class="card">
        <div class="card-body">
          <div class="section-title">&#x1F9E0; Cache semantique (cosine &ge; 0.92 &mdash; TTL 24h)</div>
          <div class="row g-3">

            <div class="col-6 col-md-3">
              <div class="p-3 rounded-3" style="background:#f8f9fa;">
                <div class="kpi-label">Entrees actives</div>
                <div class="kpi-value text-info">__CACHE_ACTIVE__</div>
                <div class="kpi-sub">sur __CACHE_TOTAL__ au total</div>
              </div>
            </div>

            <div class="col-6 col-md-3">
              <div class="p-3 rounded-3" style="background:#f8f9fa;">
                <div class="kpi-label">Taux de hit</div>
                <div class="kpi-value text-success">__CACHE_HIT_RATE__%</div>
                <div class="kpi-sub"><b>__CACHE_HITS__</b> appels servis depuis le cache</div>
              </div>
            </div>

            <div class="col-6 col-md-3">
              <div class="p-3 rounded-3" style="background:#f8f9fa;">
                <div class="kpi-label">Economies estimees</div>
                <div class="kpi-value text-warning">$__CACHE_SAVINGS__</div>
                <div class="kpi-sub">vs appels Bedrock directs</div>
              </div>
            </div>

            <div class="col-6 col-md-3">
              <div class="p-3 rounded-3" style="background:#f8f9fa;">
                <div class="kpi-label">Hits actifs cumules</div>
                <div class="kpi-value" style="color:#6f42c1;">__CACHE_ACTIVE_HITS__</div>
                <div class="kpi-sub">sur les entrees non expirees</div>
              </div>
            </div>

          </div>
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
                <th>Tools</th><th>RAG</th><th>Feedback</th><th>Statut</th>
              </tr>
            </thead>
            <tbody>__TBODY_TRACES__</tbody>
          </table>
        </div>
      </div>
    </div>
  </div>

  </div><!-- /tab-overview -->

  <!-- ══ Onglet Feedback ══════════════════════════════════════════════════════ -->
  <div class="tab-pane fade" id="tab-feedback">

    <!-- Filtres -->
    <div class="d-flex flex-wrap gap-2 mb-3 align-items-center">
      <div class="d-flex gap-2">
        <button class="btn btn-sm btn-outline-secondary active" id="fb-all"      onclick="filterFeedback('all')">Tous (__KPI_FB_TOTAL__)</button>
        <button class="btn btn-sm btn-outline-success"          id="fb-positive" onclick="filterFeedback('positive')">&#128077; Positifs (__KPI_FB_POS__)</button>
        <button class="btn btn-sm btn-outline-danger"           id="fb-negative" onclick="filterFeedback('negative')">&#128078; Negatifs (__KPI_FB_NEG__)</button>
      </div>
      <div class="vr mx-1"></div>
      <div class="d-flex gap-2">
        <button class="btn btn-sm btn-outline-secondary active" id="src-all"  onclick="filterSource('all')">Toutes sources</button>
        <button class="btn btn-sm btn-outline-primary"          id="src-chat" onclick="filterSource('chat')">&#128172; Chatbot</button>
        <button class="btn btn-sm btn-outline-warning"          id="src-quiz" onclick="filterSource('quiz')">&#10067; Quiz</button>
      </div>
    </div>

    <div id="feedback-list">__FEEDBACK_CARDS__</div>

    <p id="fb-empty" class="text-muted text-center py-5" style="display:none;">
      Aucune réponse notée pour ce filtre.
    </p>

  </div><!-- /tab-feedback -->

  </div><!-- /tab-content -->

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
const FEAT_COLORS = { chat: '#0d6efd', description_rewrite: '#6f42c1', chat_cached: '#20c997', quiz: '#ffc107' };
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

// ── Toggle texte complet ──────────────────────────────────────────────────────
function toggleFull(id) {
  const short = document.getElementById(id + '-short');
  const full  = document.getElementById(id + '-full');
  const link  = event.target;
  if (full.style.display === 'none') {
    short.style.display = 'none';
    full.style.display  = '';
    link.textContent    = 'Réduire';
  } else {
    short.style.display = '';
    full.style.display  = 'none';
    link.textContent    = 'Voir tout';
  }
}

// ── Filtres onglet Feedback (feedback type + source) ─────────────────────────
let _activeFb  = 'all';
let _activeSrc = 'all';

function applyFilters() {
  document.querySelectorAll('[data-fb]').forEach(el => {
    const fbOk  = _activeFb  === 'all' || el.dataset.fb      === _activeFb;
    const srcOk = _activeSrc === 'all' || el.dataset.feature  === _activeSrc;
    el.style.display = (fbOk && srcOk) ? '' : 'none';
  });
  const visible = document.querySelectorAll('[data-fb]').length -
                  document.querySelectorAll('[data-fb][style*="display: none"]').length;
  document.getElementById('fb-empty').style.display = visible === 0 ? '' : 'none';
}

function filterFeedback(type) {
  _activeFb = type;
  ['all','positive','negative'].forEach(t =>
    document.getElementById('fb-' + t).classList.toggle('active', t === type)
  );
  applyFilters();
}

function filterSource(src) {
  _activeSrc = src;
  ['all','chat','quiz'].forEach(t =>
    document.getElementById('src-' + t).classList.toggle('active', t === src)
  );
  applyFilters();
}
</script>
</body>
</html>"""


# ── Helpers de rendu ───────────────────────────────────────────────────────────

def _badge(feature: str) -> str:
    cls = {"chat": "primary", "quiz": "warning", "chat_cached": "info"}.get(feature, "secondary")
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
    c   = stats["cache"]

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
        fb = r.get("feedback")
        feedback_cell = ('&#128077;' if fb == "positive"
                         else '&#128078;' if fb == "negative"
                         else '<span class="text-muted">—</span>')
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
            f'<td>{feedback_cell}</td>'
            f'<td>{status}</td></tr>'
        )

    # Hauteur dynamique du chart top tools
    tools_height = max(60, len(stats["top_tools"]) * 32)

    now = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")

    fb  = stats["feedback"]

    # Cartes feedback détaillées
    feedback_cards = ""
    for r in stats["feedback_traces"]:
        is_pos  = r["feedback"] == "positive"
        border  = "#198754" if is_pos else "#dc3545"
        icon    = "👍" if is_pos else "👎"
        label   = "Positif" if is_pos else "Negatif"
        badge   = "success" if is_pos else "danger"
        tools   = ", ".join(tc["name"] for tc in r["tool_calls"]) if r["tool_calls"] else "—"
        dt      = r["created_at"][:16].replace("T", " ") if r["created_at"] else "—"
        q_text   = r["user_message"][:200] + ("…" if len(r["user_message"]) > 200 else "")
        a_short  = r["assistant_response"][:300] + ("…" if len(r["assistant_response"]) > 300 else "")
        a_full   = r["assistant_response"].replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
        card_id  = "fb-" + r["id"][:8]
        voir_tout = (
            '<a href="#" class="ms-1 small" onclick="toggleFull(\'' + card_id + '\');return false;">Voir tout</a>'
            if len(r["assistant_response"]) > 300 else ""
        )
        feedback_cards += (
            '<div class="card mb-3" data-fb="' + r["feedback"] + '" data-feature="' + r["feature"] + '" style="border-left:4px solid ' + border + ';">'
            '<div class="card-body py-3">'
            '<div class="d-flex justify-content-between align-items-start mb-2">'
            '<span class="badge bg-' + badge + '">' + icon + ' ' + label + '</span>'
            '<span class="text-muted small">' + dt + ' &middot; ' + r["feature"] + ' &middot; ' + str(r["latency_ms"]) + ' ms'
            ' &middot; RAG ' + str(r["rag_chunks_used"] or 0) + ' &middot; Tools: ' + tools + '</span>'
            '</div>'
            '<div class="mb-2">'
            '<div class="small text-muted fw-semibold mb-1">Question utilisateur</div>'
            '<div class="p-2 rounded" style="background:#f8f9fa;font-size:.85rem;">' + q_text + '</div>'
            '</div>'
            '<div>'
            '<div class="small text-muted fw-semibold mb-1">Réponse PawBuddy</div>'
            '<div class="p-2 rounded" style="background:#f8f9fa;font-size:.85rem;">'
            '<span id="' + card_id + '-short">' + a_short + '</span>'
            '<span id="' + card_id + '-full" style="display:none;">' + a_full + '</span>'
            + voir_tout +
            '</div>'
            '</div>'
            '</div>'
            '</div>\n'
        )

    html = _ADMIN_TEMPLATE
    html = html.replace("__TOKEN__",              token)
    html = html.replace("__KPI_SATISFACTION__",   str(fb["satisfaction_rate"]))
    html = html.replace("__KPI_FB_POS__",         str(fb["positive"]))
    html = html.replace("__KPI_FB_NEG__",         str(fb["negative"]))
    html = html.replace("__KPI_FB_TOTAL__",       str(fb["total"]))
    html = html.replace("__BADGE_NEG_CLASS__",    "bg-danger" if fb["negative"] > 0 else "bg-secondary")
    html = html.replace("__FEEDBACK_CARDS__",     feedback_cards if feedback_cards else "")
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
    cache_hit_rate = round(c["cached_calls"] / c["total_chat_calls"] * 100, 1) if c["total_chat_calls"] else 0.0
    html = html.replace("__CACHE_ACTIVE__",       str(c["active_entries"]))
    html = html.replace("__CACHE_TOTAL__",        str(c["total_entries"]))
    html = html.replace("__CACHE_HIT_RATE__",     str(cache_hit_rate))
    html = html.replace("__CACHE_HITS__",         str(c["cached_calls"]))
    html = html.replace("__CACHE_SAVINGS__",      f'{c["estimated_savings"]:.5f}')
    html = html.replace("__CACHE_ACTIVE_HITS__",  str(c["active_hits"]))
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