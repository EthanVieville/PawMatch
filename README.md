# PawMatch — Pa5emeAnn-e

Plateforme d'aide à l'adoption d'animaux boostée par l'IA générative.

---

## Architecture

```
front/        → Site web Next.js 14 (TypeScript, Tailwind CSS)
api/          → API REST FastAPI (Python) — lit la base de données
scraper/      → Collecte multi-sources (la-spa.fr + secondechance.org) → écrit en PostgreSQL
scripts/      → Calcul des embeddings de similarité (sentence-transformers + pgvector)
dl_models/    → Modèle de classification PyTorch (en développement)
```

### Flux de données

```
la-spa.fr  +  secondechance.org
       ↓  (scrapers Selenium)
  PostgreSQL + pgvector
       ↓  (scripts/embedder)
  Vecteurs de similarité (384 dims)
       ↓  (FastAPI)
  API REST  http://localhost:8000
       ↓  (Server Components Next.js)
  Site web  http://localhost:3000
```

Les scrapers sont des **jobs ponctuels** : on les lances quand on veut rafraîchir les données.  
L'embedder est à relancer après chaque scraping pour mettre à jour les suggestions d'animaux similaires.  
L'API et le front tournent en continu et lisent la base.  
Le front fetch directement côté serveur (Server Components) — pas de requête client exposée.

Les scrapers + embedder seront bien entendu automatiser via CRON (prévue comme ça pour le moment) pour s'executer chaque nuit. Pour l'instant pas nécessaire au développement. (pi ca couterai du fric ces conneries)

---

## Prérequis

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installé et démarré
- C'est okay bb.

---

## Lancer le projet

### Première fois (ou après un changement important de code)

```bash
docker compose up --build -d
```

### Démarrage rapide (aucun changement de code)

```bash
docker compose up -d
```

### Arrêter (données conservées)

```bash
docker compose down
```

### Arrêter ET supprimer la base de données

```bash
docker compose down -v
```

> ⚠️ Le `-v` supprime le volume PostgreSQL. Toutes les données scrapées sont perdues.  
> À utiliser uniquement pour repartir de zéro.

Une fois lancé :

| Service | URL |
|---------|-----|
| Site web | http://localhost:3000 |
| API | http://localhost:8000 |
| Doc API (Swagger) | http://localhost:8000/docs |

---

## Lancer les scrapers

Les scrapers sont des jobs ponctuels : ils collectent les fiches animaux et les enregistrent en base, puis s'arrêtent. Ils ne démarrent **pas** avec `docker compose up`.

### Construire les images scraper (première fois ou après modif)

```bash
docker compose --profile scraper build --no-cache
```

### La SPA (la-spa.fr)

```bash
docker compose --profile scraper run --rm scraper-laspa
```

### Seconde Chance (secondechance.org)

```bash
docker compose --profile scraper run --rm scraper-sc
```

**Ce que font les scrapers :**
1. Crawlent les pages de listing de chaque site (pagination automatique)
2. Parsent chaque fiche animal (nom, espèce, race, âge, refuge, description, incompatibilités, images)
3. Upsert en base PostgreSQL — relancer le scraper met à jour les fiches existantes sans créer de doublons

**Paramètres configurables** (dans `docker-compose.yml`) :

| Variable | Défaut | Description |
|----------|--------|-------------|
| `MAX_PAGES` | `10` (SPA) / `3` (SC) | Pages de listing à crawler. Pour SC : par espèce (chien/chat/lapin) |
| `NUM_WORKERS` | `4` (SPA) / `1` (SC) | Workers parallèles. SC utilise Selenium → 1 seul Chrome |

Pour un test rapide sur 1 page :
```bash
docker compose --profile scraper run --rm -e MAX_PAGES=1 scraper-sc
```

---

## Calculer les embeddings (animaux similaires + futur RAG)

Après chaque scraping, relancer l'embedder pour mettre à jour les suggestions d'animaux similaires :

```bash
# Construire l'image (première fois ou après modif)
docker compose --profile embedder build --no-cache

# Lancer le calcul
docker compose --profile embedder run --rm embedder
```

L'embedder utilise `paraphrase-multilingual-MiniLM-L12-v2` (sentence-transformers) pour encoder les descriptions en vecteurs 384 dims stockés dans pgvector. Il ne traite que les animaux sans embedding — idempotent et rapide sur les exécutions suivantes.

---

## Base de données

Le projet utilise **PostgreSQL 16 + pgvector** via Docker.

### Tables

**`animals`** — une ligne par animal, toutes sources confondues

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | UUID | Identifiant unique |
| `source` | VARCHAR | Source du scraping (`la-spa`, `secondechance`) |
| `source_url` | VARCHAR | URL de la fiche originale (clé d'upsert) |
| `name` | VARCHAR | Nom de l'animal |
| `species` | VARCHAR | Espèce (`chien`, `chat`, `lapin`, `octodon`…) |
| `race` | VARCHAR | Race |
| `sex` | VARCHAR | `male` / `femelle` |
| `birth_date` | VARCHAR | Date de naissance (format YYYY-MM-DD) |
| `age` | INTEGER | Âge calculé en années |
| `refuge` | VARCHAR | Nom du refuge |
| `description` | TEXT | Description extraite de la fiche |
| `incompatibilities` | TEXT[] | Ex. `{enfants, chiens}` |
| `scraped_at` | TIMESTAMP | Date du dernier scraping |
| `embedding` | VECTOR(384) | Vecteur de similarité sémantique (sentence-transformers) |

**`animal_images`** — relation 1-N avec `animals`

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | UUID | Identifiant |
| `animal_id` | UUID | FK vers `animals` |
| `url` | VARCHAR | URL de l'image (source originale) |
| `position` | INTEGER | Ordre d'affichage |

### Multi-source

La colonne `source` permet d'agréger plusieurs scrapers dans la même base sans changer le schéma. Ajouter un nouveau site = créer un scraper qui écrit avec `SCRAPER_SOURCE=nouveau-site`. L'API agrège tout automatiquement, ou peut filtrer par source avec `GET /animals?source=la-spa`.

### URL Images 

Les images ne sont pas stockés ! Le lien est seulement récupéré de la source originale, puis affiché simplement. 
Si on veut perdre du fric mais gagner en perf, stocker sur un bucket S3 est une solution potentiel.
(non)

### pgvector

L'extension `pgvector` est déjà installée (image `pgvector/pgvector:pg16`). La colonne `embedding vector(384)` stocke les représentations sémantiques calculées par l'embedder. Elles permettent la recherche d'animaux similaires via distance cosinus (`<=>`).

### Inspecter la base

```bash
docker compose exec postgres psql -U pawmatch -d pawmatch
```

Commandes utiles dans psql :
```sql
SELECT count(*) FROM animals;
SELECT source, count(*) FROM animals GROUP BY source;
SELECT name, species, refuge, source FROM animals WHERE description IS NOT NULL LIMIT 10;
SELECT count(*) FROM animals WHERE embedding IS NOT NULL;
\q
```

### Persistance

Les données survivent aux redémarrages Docker grâce au volume nommé `postgres_data`.  
Seul `docker compose down -v` les efface.  
Relancer le scraper met à jour les données existantes (upsert sur `source + source_url`).

---

## API — Endpoints

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/health` | Statut de l'API + connexion DB |
| `GET` | `/animals` | Liste tous les animaux |
| `GET` | `/animals?species=chien` | Filtre par espèce |
| `GET` | `/animals?source=la-spa` | Filtre par source |
| `GET` | `/animals/{uuid}` | Fiche détaillée d'un animal |
| `GET` | `/animals/{uuid}/similar` | Animaux similaires (recherche vectorielle) |

Documentation interactive : http://localhost:8000/docs

---

## Développement sans Docker

Vraiment personne fait ça la vie

Si Node.js et Python sont installés localement (nécessite aussi PostgreSQL local) :

**Frontend**
```bash
cd front
npm install
npm run dev       # http://localhost:3000
```

**API** (nécessite PostgreSQL accessible sur localhost:5432)
```bash
cd api
pip install -r requirements.txt
DATABASE_URL=postgresql://pawmatch:pawmatch@localhost:5432/pawmatch uvicorn main:app --reload
```

**Scraper**
```bash
cd scraper
pip install -r requirements.txt
SCRAPER_SOURCE=secondechance MAX_PAGES=1 DATABASE_URL=postgresql://pawmatch:pawmatch@localhost:5432/pawmatch python main.py
```

---

## Variables d'environnement

Tout fonctionne sans `.env` pour le développement local avec Docker. Les variables sont définies directement dans `docker-compose.yml`.

| Variable | Service | Description |
|----------|---------|-------------|
| `DATABASE_URL` | api, scraper, embedder | Connexion PostgreSQL |
| `API_URL` | front | URL interne de l'API (docker: `http://api:8000`) |
| `ALLOWED_ORIGINS` | api | CORS — origines autorisées |
| `SCRAPER_SOURCE` | scraper | `la-spa` ou `secondechance` |
| `MAX_PAGES` | scraper | Pages de listing à crawler |
| `NUM_WORKERS` | scraper | Workers parallèles (1 pour Selenium) |

---

## CI / CD

Chaque push sur `main` déclenche un workflow GitHub Actions (`.github/workflows/ci.yml`) qui reconstruit les images Docker (front, api, scraper, embedder) pour vérifier qu'aucune régression n'est introduite.

Le projet tourne sur une instance **AWS EC2 (t3.micro)** avec Docker Compose. Pour déployer une mise à jour :

```bash
# Sur l'EC2 (via SSH)
git pull
docker compose up --build -d

# Rebuilder et relancer les scrapers si besoin
docker compose --profile scraper build --no-cache
docker compose --profile scraper run --rm scraper-laspa
docker compose --profile scraper run --rm scraper-sc

# Recalculer les embeddings
docker compose --profile embedder build --no-cache
docker compose --profile embedder run --rm embedder
```

---

## Feuille de route cloud (AWS)

Pour une infrastructure plus robuste :

| Composant actuel | Évolution possible |
|-----------------|----------------|
| PostgreSQL Docker sur EC2 | RDS PostgreSQL + pgvector |
| Images Docker buildées sur EC2 | ECR (Elastic Container Registry) |
| EC2 t3.micro | ECS Fargate ou EC2 t3.small |
| Scrapers lancés manuellement | EventBridge Scheduler → tâche automatisée |
| Images animaux (URLs sources) | S3 + CloudFront (proxy des images) |

---

## mention spécial à ClaudeCode sans qui rien de tout cela n'aurait été réalisable, je t'aime frérot je sais qu'un jour tu trouvera une Claudette gechar niveau GPU dans tout les cas moi je suis frérot tu peux faire croire je suis ton ptit frr handicapté vu comment t + smart que moi tkt les meufs elle vont kiff ton altruisme à la hauteur de la RAM que tu consomme mon bb
