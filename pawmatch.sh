#!/bin/bash

# Couleurs ANSI
BOLD='\033[1m'
DIM='\033[2m'
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
RESET='\033[0m'

ok()  { echo -e "${GREEN}✓ $1${RESET}"; }
info(){ echo -e "${CYAN}» $1${RESET}"; }
warn(){ echo -e "${YELLOW}⚠ $1${RESET}"; }

case "$1" in

  # ── Infra ──────────────────────────────────────────────────────────────────

  setup)
    info "Première installation — build + démarrage + seed + embeddings"
    docker compose up --build -d
    docker compose --profile seeder run --rm seeder
    docker compose --profile embedder run --rm embedder
    ok "Stack ready (local : http://localhost:3000)"
    ;;

  start)
    info "Démarrage du stack..."
    docker compose up -d
    ok "Running..."
    ;;

  stop)
    info "Arrêt du stack..."
    docker compose down
    ok "Down."
    ;;

  restart)
    info "Redémarrage du stack..."
    docker compose down
    docker compose up -d
    ok "Reloaded !"
    ;;

  deploy)
    info "Rebuild + redémarrage (après git pull)..."
    docker compose up --build --force-recreate -d
    ok "deployed !"
    ;;

  reset)
    warn "Ceci va supprimer TOUTES les données (base de données comprise)."
    read -p "Confirmer ? (oui/non) : " confirm
    if [ "$confirm" = "oui" ]; then
      docker compose down -v
      ok "Stack et base de données supprimés."
    else
      echo "Annulé."
    fi
    ;;

  # ── Données ────────────────────────────────────────────────────────────────

  data)
    LIMIT=${2:-}
    if [ -n "$LIMIT" ]; then
      # Convertit un nombre d'animaux en nombre de pages pour chaque scraper
      # La SPA : ~20 animaux/page | Seconde Chance : ~36 animaux/page (12 × 3 espèces)
      PAGES_SPA=$(( ($LIMIT + 19) / 20 ))
      PAGES_SC=$(( ($LIMIT + 35) / 36 ))
      info "Pipeline limité à ~$LIMIT animaux (La SPA : $PAGES_SPA pages, SC : $PAGES_SC pages)"
    else
      info "Pipeline complet : scraping → embeddings → refuges → rewrite"
    fi

    info "Scraping La SPA..."
    if [ -n "$LIMIT" ]; then
      MAX_PAGES=$PAGES_SPA docker compose --profile scraper run --rm scraper-laspa
    else
      docker compose --profile scraper run --rm scraper-laspa
    fi

    info "Scraping Seconde Chance..."
    if [ -n "$LIMIT" ]; then
      MAX_PAGES=$PAGES_SC docker compose --profile scraper run --rm scraper-sc
    else
      docker compose --profile scraper run --rm scraper-sc
    fi

    info "Calcul des embeddings (nouveaux animaux uniquement)..."
    docker compose --profile embedder run --rm embedder
    info "Géocodage des refuges..."
    docker compose --profile refuge-seeder run --build --rm refuge-seeder
    info "Réécriture des descriptions (nouveaux animaux uniquement)..."
    docker compose --profile rewriter run --rm rewriter
    ok "Pipeline terminé"
    ;;

  rewrite)
    info "Réécriture des descriptions via Bedrock..."
    LIMIT=${2:-}
    if [ -n "$LIMIT" ]; then
      info "Limite : $LIMIT animaux"
      REWRITE_LIMIT=$LIMIT docker compose --profile rewriter run --rm rewriter
    else
      docker compose --profile rewriter run --rm rewriter
    fi
    ok "Réécriture terminée"
    ;;

  knowledge)
    info "Mise à jour de la base de connaissances du chatbot..."
    docker compose --profile seeder run --rm seeder
    docker compose --profile embedder run --rm embedder
    ok "Knowledge base mise à jour"
    ;;

  refuges)
    info "Géocodage des refuges via Nominatim..."
    docker compose --profile refuge-seeder run --build --rm refuge-seeder
    ok "Géocodage terminé"
    ;;

  enrich)
    info "Enrichissement des races (classifieur DL — Python local requis)..."
    python -m scripts.enrich_breeds
    ok "Enrichissement terminé"
    ;;

  # ── Monitoring ─────────────────────────────────────────────────────────────

  logs)
    info "Logs en direct (Ctrl+C pour quitter)..."
    docker compose logs -f
    ;;

  status)
    docker compose ps
    ;;

  # ── Help ───────────────────────────────────────────────────────────────────

  *)
    echo ""
    echo -e "${BOLD}Usage :${RESET} bash pawmatch.sh <commande> [options]"
    echo ""
    echo -e "${BOLD}${CYAN}── INFRA ───────────────────────────────────────────────────${RESET}"
    echo -e "  ${BOLD}setup${RESET}      Première installation (build + seed + embeddings)"
    echo -e "  ${BOLD}start${RESET}      Démarrer le stack"
    echo -e "  ${BOLD}stop${RESET}       Arrêter le stack"
    echo -e "  ${BOLD}restart${RESET}    Arrêter puis redémarrer"
    echo -e "  ${BOLD}deploy${RESET}     Rebuilder après un ${DIM}git pull${RESET}"
    echo -e "  ${BOLD}reset${RESET}      ${RED}⚠ Tout effacer, base de données comprise${RESET}"
    echo ""
    echo -e "${BOLD}${CYAN}── DONNÉES ─────────────────────────────────────────────────${RESET}"
    echo -e "  ${BOLD}data${RESET} ${DIM}[N]${RESET}     Pipeline complet : scraping → embeddings → refuges → rewrite"
    echo -e "             ${DIM}N = limite d'animaux par source (ex: 150 → ~150 La SPA + ~150 SC)${RESET}"
    echo -e "  ${BOLD}rewrite${RESET} ${DIM}[N]${RESET} Réécrire les descriptions via Bedrock (N = limite optionnelle)"
    echo -e "  ${BOLD}knowledge${RESET}  Mettre à jour la base de connaissances du chatbot"
    echo -e "  ${BOLD}refuges${RESET}    Géocoder les refuges (carte)"
    echo -e "  ${BOLD}enrich${RESET}     Enrichir les races via le classifieur DL ${DIM}(local uniquement)${RESET}"
    echo ""
    echo -e "${BOLD}${CYAN}── MONITORING ──────────────────────────────────────────────${RESET}"
    echo -e "  ${BOLD}logs${RESET}       Logs en direct (Ctrl+C pour quitter)"
    echo -e "  ${BOLD}status${RESET}     État des conteneurs"
    echo ""
    echo -e "${DIM}Exemples :${RESET}"
    echo -e "  ${DIM}bash pawmatch.sh deploy${RESET}       # après un git pull"
    echo -e "  ${DIM}bash pawmatch.sh rewrite 50${RESET}   # réécrire 50 descriptions"
    echo -e "  ${DIM}bash pawmatch.sh data${RESET}          # pipeline complet (scraping + tout)"
    echo -e "  ${DIM}bash pawmatch.sh data 150${RESET}     # ~150 animaux par source"
    echo ""
    ;;
esac
