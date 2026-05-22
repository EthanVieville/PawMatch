#!/bin/bash

case "$1" in
  setup)
    echo ">> Build + démarrage du stack..."
    docker compose up --build -d
    echo ">> Peuplement de la knowledge base..."
    docker compose --profile seeder run --rm seeder
    echo ">> Calcul des embeddings..."
    docker compose --profile embedder run --rm embedder
    echo "✓ Done. http://localhost:3000"
    ;;
  start)
    docker compose up -d
    ;;
  stop)
    docker compose down
    ;;
  reset)
    docker compose down -v
    echo "Base de données supprimée."
    ;;
  deploy)
    echo ">> Rebuild + redémarrage..."
    docker compose up --build -d
    ;;
  data)
    echo ">> Scraping La SPA..."
    docker compose --profile scraper run --rm scraper-laspa
    echo ">> Scraping Seconde Chance..."
    docker compose --profile scraper run --rm scraper-sc
    echo ">> Calcul des embeddings..."
    docker compose --profile embedder run --rm embedder
    echo ">> Géocodage des refuges..."
    docker compose --profile refuge-seeder run --build --rm refuge-seeder
    echo "✓ Done."
    ;;
  refuges)
    echo ">> Géocodage des refuges via Nominatim..."
    docker compose --profile refuge-seeder run --build --rm refuge-seeder
    echo "✓ Done."
    ;;
  knowledge)
    echo ">> Mise à jour de la knowledge base..."
    docker compose --profile seeder run --rm seeder
    echo ">> Calcul des embeddings..."
    docker compose --profile embedder run --rm embedder
    echo "✓ Done."
    ;;
  enrich)
    echo ">> Enrichissement des races (DL — requiert Python local + modèle .pth)..."
    python -m scripts.enrich_breeds
    echo "✓ Done."
    ;;
  logs)
    docker compose logs -f
    ;;
  status)
    docker compose ps
    ;;
  *)
    echo ""
    echo "Usage: bash pawmatch.sh <commande>"
    echo ""
    echo "  setup      Première installation (build + seed + embeddings)"
    echo "  start      Démarrage rapide"
    echo "  stop       Arrêter le stack"
    echo "  reset      Tout effacer (DB comprise)"
    echo "  deploy     Rebuild après changement de code"
    echo "  data       Rafraîchir les animaux (scraping + embeddings + refuges)"
    echo "  refuges    Géocoder les refuges via Nominatim (map)"
    echo "  knowledge  Mettre à jour la knowledge base du chatbot"
    echo "  enrich     Enrichir les races avec le classifieur DL (local uniquement)"
    echo "  logs       Logs en direct"
    echo "  status     État des services"
    echo ""
    ;;
esac
