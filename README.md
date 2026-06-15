# PawMatch

Plateforme d'aide à l'adoption d'animaux boostée par l'IA générative.

---

## Architecture

```
front/        → Site web Next.js 14 (TypeScript, Tailwind CSS)
api/          → API REST FastAPI (Python) — chatbot LLM + LLMOps
scraper/      → Collecte multi-sources (la-spa.fr + secondechance.org)
scripts/      → Jobs ponctuels : embeddings, rewrite descriptions, seed knowledge, géocodage
dl_models/    → Classifieur de race PyTorch (MobileNetV2, 37 races Oxford-IIIT Pet)
```

### Flux de données

```
la-spa.fr  +  secondechance.org
      ed_refuges     → coordonnées GPS (Nominatim)
       ↓  scripts/enrich_breeds    → race_predicted (MobileNetV2)
  API REST  http://localhost:8000
       ↓  Server Components Next.js
  Site web  http://localhost:3000

  Chatbot PawBuddy
       ↓  cache sémantique pgvector (hit → réponse instantanée, coût $0)
       ↓  miss → RAG knowledge_chunks + tool use (search_animals, etc.)
  Amazon Bedrock (Claude Haiku 4.5, eu-west-1)  ←→  llm_traces (tokens, coût, latence)
       ↓  SSE streaming token par token ↓  scrapers Selenium
  PostgreSQL + pgvector
       ↓  scripts/embedder         → vecteurs de similarité 384 dims
       ↓  scripts/rewrite          → descriptions réécrites via Bedrock (Claude Haiku)
       ↓  scripts/se
```

---

## Prérequis

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installé et démarré
- Un fichier `.env` à la racine (copier `.env.example` et remplir les valeurs AWS)
- C'est tout.

---

## Lancer le projet

Toutes les commandes passent par `pawmatch.sh` :

```bash
bash pawmatch.sh <commande>
```

| | Commande | Description |
|---|---|---|
| **INFRA** | `setup` | Première installation — build, démarrage, seed, embeddings |
| | `start` | Démarrer le stack |
| | `stop` | Arrêter le stack |
| | `restart` | Arrêter puis redémarrer |
| | `deploy` | Rebuild après un `git pull` |
| | `reset` | ⚠️ Tout effacer, base de données comprise |
| **DONNÉES** | `data [N]` | Pipeline complet — scraping → embeddings → refuges → rewrite LLM. `N` = limite d'animaux par source (ex: `data 150`) |
| | `rewrite [N]` | Réécrire les descriptions via Bedrock. `N` = limite optionnelle |
| | `knowledge` | Mettre à jour la base de connaissances du chatbot |
| | `refuges` | Géocoder les refuges (carte) |
| | `enrich` | Prédire les races via le classifieur DL *(Python local requis)* |
| **MONITORING** | `logs` | Logs en direct (Ctrl+C pour quitter) |
| | `status` | État des conteneurs |

```bash
bash pawmatch.sh setup          # première fois
bash pawmatch.sh deploy         # après un git pull
bash pawmatch.sh data           # pipeline complet
bash pawmatch.sh data 150       # ~150 animaux par source
bash pawmatch.sh rewrite 50     # réécrire max 50 descriptions
```

URLs locales :

| Service | URL |
|---|---|
| Site web | http://localhost:3000 |
| API + Swagger | http://localhost:8000/docs |
| Dashboard LLMOps | http://localhost:8000/admin?token=`<ADMIN_TOKEN>` |

---

## LLMOps

Toutes les interactions LLM sont tracées en base (`llm_traces`) avec tokens, coût, latence et outils utilisés. Un dashboard admin regroupe les métriques.

### Dashboard

```bash
# En local
http://localhost:8000/admin?token=<ADMIN_TOKEN>

# En production via SSH tunnel
ssh -L 8001:localhost:8000 ec2-user@<ip-ec2>
# → http://localhost:8001/admin?token=<ADMIN_TOKEN>
```

Métriques disponibles : coût total, projection mensuelle, taux d'erreur, latences p50/p90/p99, taux de cache hit, économies estimées, top outils, répartition par feature, 100 dernières traces.

### Cache sémantique

Les requêtes sans contexte (hors fiche animal, hors historique de conversation) sont mises en cache via similarité cosinus pgvector. Seuil : **0.92**, TTL : **24h**.

| | Appel Bedrock | Cache hit |
|---|---|---|
| Latence | ~4 000 ms | ~30 ms |
| Coût | ~$0.00016 | **$0** |

### Réécriture des descriptions

Les descriptions brutes issues du scraping sont reformulées par Claude Haiku en texte clair et chaleureux, stockées dans `description_rewritten`. Affichées sur les fiches avec le badge ✨ PawBuddy.

Coût indicatif : ~$0.046 pour 500 animaux.

---

## Chatbot PawBuddy

Widget flottant sur toutes les pages. Alimenté par **Amazon Bedrock (Claude Haiku 4.5)** via RAG sur la base PostgreSQL.

- Recherche d'animaux avec liens cliquables vers les fiches
- Informations sur les démarches d'adoption
- Conseils de soins par espèce
- Streaming token par token, conversation persistante (localStorage)
- Tool use : `search_animals`, `search_knowledge`, `get_animal`, `search_animal_by_name`
- Cache sémantique pour les questions génériques

---

## Base de données

PostgreSQL 16 + pgvector. Les données survivent aux redémarrages via le volume Docker `postgres_data`. Seul `bash pawmatch.sh reset` (= `docker compose down -v`) les efface.

| Table | Description |
|---|---|
| `animals` | Un animal par ligne — toutes sources confondues |
| `animal_images` | Images (relation 1-N avec `animals`) |
| `refuges` | Coordonnées GPS géocodées via Nominatim |
| `knowledge_chunks` | Base de connaissances pour le RAG du chatbot |
| `llm_traces` | Trace de chaque appel LLM (tokens, coût, latence, outils) |
| `llm_cache` | Cache sémantique des réponses du chatbot |

```bash
# Inspecter la base
docker compose exec postgres psql -U pawmatch -d pawmatch
```

```sql
SELECT source, count(*) FROM animals GROUP BY source;
SELECT count(*) FROM animals WHERE embedding IS NOT NULL;
SELECT count(*) FROM animals WHERE description_rewritten IS NOT NULL;
SELECT feature, count(*), round(sum(cost_usd)::numeric, 5) FROM llm_traces GROUP BY feature;
```

---

## API — Endpoints

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Statut API + connexion DB |
| `GET` | `/animals` | Liste des animaux (filtres : `species`, `source`) |
| `GET` | `/animals/{uuid}` | Fiche détaillée |
| `GET` | `/animals/{uuid}/similar` | Animaux similaires (pgvector) |
| `GET` | `/refuges` | Refuges géocodés pour la carte |
| `POST` | `/animals` | Créer une annonce particulier (prédit la race via DL) |
| `POST` | `/predict-breed` | Prédiction de race depuis une image base64 |
| `POST` | `/chat` | Chatbot PawBuddy — streaming SSE |
| `GET` | `/admin` | Dashboard LLMOps *(token requis)* |

---

## Deep Learning — Classifieur de race

Modèle **MobileNetV2** multi-tâches (backbone ImageNet) — 3 têtes : espèce, couleur, race (37 races Oxford-IIIT Pet).

| Métrique | Résultat |
|---|---|
| Précision espèce (chat/chien) | **95 %** |
| Précision race (animaux Oxford-mappables) | **44 %** |

**Workflow :** job ponctuel après scraping via `bash pawmatch.sh enrich` (Python local requis).  
**Sur EC2 :** ouvrir un tunnel SSH vers le PostgreSQL de l'EC2, puis lancer `enrich` localement.

```bash
ssh -L 5432:localhost:5432 ec2-user@<ip-ec2>   # terminal 1 — laisser ouvert
DATABASE_URL=postgresql://pawmatch:pawmatch@localhost:5432/pawmatch python -m scripts.enrich_breeds
```

**Prédiction temps réel :** pour les annonces de particuliers (`POST /animals`), la race est prédite au moment du dépôt.

---

## Variables d'environnement

Copier `.env.example` en `.env`. Toutes les variables ont des valeurs par défaut sauf les credentials AWS et le token admin.

| Variable | Description |
|---|---|
| `AWS_REGION` | Région Bedrock (`eu-west-1`) |
| `AWS_ACCESS_KEY_ID` | Clé IAM — **dev local uniquement** (IAM role sur EC2) |
| `AWS_SECRET_ACCESS_KEY` | Secret IAM — **dev local uniquement** |
| `ADMIN_TOKEN` | Token d'accès au dashboard LLMOps |
| `BEDROCK_MODEL` | Override du modèle Bedrock (optionnel) |

---

## CI / CD

### Déploiement continu (CD)

Chaque push sur `main` déclenche automatiquement `.github/workflows/deploy.yml` :

1. Démarre l'EC2 si elle est arrêtée (via AWS SDK)
2. Ouvre le port 22 temporairement pour le runner GitHub Actions
3. SSH → `git pull origin main` + `bash pawmatch.sh deploy`
4. Referme le port 22
5. Health check sur le port 3000

Secrets GitHub requis : `AWS_DEPLOY_KEY_ID`, `AWS_DEPLOY_SECRET`, `EC2_INSTANCE_ID`, `EC2_HOST`, `EC2_USER`, `EC2_SSH_KEY`.

Le déploiement peut aussi être déclenché manuellement depuis GitHub Actions → **Run workflow**.

---

## Scraping automatique

Le pipeline de données est géré par `.github/workflows/scrape.yml`. Il est **désactivé par défaut** pour garder le contrôle sur les coûts et le volume de données.

**Déclencher un run manuel (recommandé pour tester) :**

GitHub Actions → *Scrape — Daily data pipeline* → **Run workflow** → renseigner la limite d'animaux (défaut : 30 par source).

**Activer le CRON quotidien (6h UTC) :**

GitHub Actions → *Scrape — Daily data pipeline* → **Enable workflow**.

**Désactiver :**

Même endroit → **Disable workflow**.

Ce que fait chaque run :
```
scraping La SPA + Seconde Chance (N animaux par source)
  → calcul des embeddings (nouveaux animaux uniquement)
  → géocodage des refuges (nouveaux refuges uniquement)
  → réécriture des descriptions via Bedrock (nouveaux animaux uniquement)
```

Coût indicatif pour 30 animaux par source : **< $0.05** (rewrite Bedrock uniquement).

---

## Documentation 

Voir les documents dans documentation/ pour plus de détails sur tout.
