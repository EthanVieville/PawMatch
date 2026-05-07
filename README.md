# PawMatch — Pa5emeAnn-e

Plateforme d'aide à l'adoption d'animaux boostée par l'IA générative.

---

## Architecture

```
front/        → Site web Next.js 14 (TypeScript, Tailwind CSS)
api/          → API REST FastAPI (Python) — lit la base de données
scraper/      → Collecte Selenium sur la-spa.fr → écrit en PostgreSQL
dl_models/    → Modèle de classification PyTorch (chat/chien, couleur)
```

### Flux de données

```
la-spa.fr
    ↓  (scraper Selenium)
PostgreSQL + pgvector
    ↓  (FastAPI)
API REST  http://localhost:8000
    ↓  (Server Components Next.js)
Site web  http://localhost:3000
```

Le scraper est un **job ponctuel** : on le lance quand on veut rafraîchir les données. Faudra le configure via AWS pour automatiser tout ça  
L'API et le front tournent en continu et lisent la base.  
Le front fetchs directement côté serveur (Server Components) — pas de requête client exposée.

---

## Prérequis

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installé et démarré
- C'est okay bb.

---

## Lancer le projet

### Première fois (ou après un changement de code)

```bash
docker compose up --build
```

### Démarrage rapide (aucun changement de code)

```bash
docker compose up
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

## Lancer le scraper

Le scraper est un job ponctuel : il collecte les fiches animaux sur la-spa.fr et les enregistre en base, puis s'arrête. Il ne démarre **pas** avec `docker compose up`.
Idéalement à lancer quand docker compose up (--build) est en cours ^^

```bash
docker compose --profile scraper run --build scraper
```

> Le `--build` est important la première fois (ou après une modif du scraper) pour reconstruire l'image.  
> Les fois suivantes sans changement de code : `docker compose --profile scraper run scraper`

**Ce que fait le scraper :**
1. Démarre Chrome headless dans Docker
2. Crawle les pages de listing de la-spa.fr (pagination automatique)
3. Parse chaque fiche animal (nom, espèce, race, âge, refuge, description, incompatibilités, images)
4. Upsert en base PostgreSQL — relancer le scraper met à jour les fiches existantes sans créer de doublons

**Paramètres configurables** (via variables d'environnement dans `docker-compose.yml`) :

| Variable | Défaut | Description |
|----------|--------|-------------|
| `MAX_PAGES` | `10` | Nombre de pages de listing à crawler |
| `NUM_WORKERS` | `4` | Workers Chrome parallèles |
| `SCRAPER_SOURCE` | `la-spa` | Identifiant de la source (utile quand on ajoutera d'autres sites) |

Pour surcharger ponctuellement (testé dans term VScode le reste jsp) :
```powershell
$env:MAX_PAGES=20; docker compose --profile scraper run scraper
```

---

## Base de données

Le projet utilise **PostgreSQL 16 + pgvector** via Docker.

### Tables

**`animals`** — une ligne par animal, toutes sources confondues

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | UUID | Identifiant unique |
| `source` | VARCHAR | Source du scraping (`la-spa`, futur: `gay`…) |
| `source_url` | VARCHAR | URL de la fiche originale (clé d'upsert) |
| `name` | VARCHAR | Nom de l'animal |
| `species` | VARCHAR | Espèce (`chien`, `chat`, `nac`…) |
| `race` | VARCHAR | Race |
| `sex` | VARCHAR | `male` / `femelle` |
| `birth_date` | VARCHAR | Date de naissance (format YYYY-MM-DD) |
| `age` | INTEGER | Âge calculé en années |
| `refuge` | VARCHAR | Nom du refuge |
| `description` | TEXT | Description extraite de la fiche |
| `incompatibilities` | TEXT[] | Ex. `{enfants, chiens}` |
| `scraped_at` | TIMESTAMP | Date du dernier scraping |
| `embedding` | VECTOR(1536) | Réservé pour le chatbot LLM (NULL pour l'instant) |

**`animal_images`** — relation 1-N avec `animals`

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | UUID | Identifiant |
| `animal_id` | UUID | FK vers `animals` |
| `url` | VARCHAR | URL de l'image (source originale) |
| `position` | INTEGER | Ordre d'affichage |

### Multi-source

La colonne `source` permet d'agréger plusieurs scrapers dans la même base sans changer le schéma. Ajouter un deuxième site = créer un nouveau scraper qui écrit avec `SCRAPER_SOURCE=nouveau-site`. L'API agrège tout automatiquement, ou peut filtrer par source avec `GET /animals?source=la-spa`.

### pgvector

L'extension `pgvector` est déjà installée (image `pgvector/pgvector:pg16`). La colonne `embedding` est prête pour le RAG quand on branchera le LLM : "je cherche un chien calme pour appartement" → recherche vectorielle sur les descriptions. Ca dahak

### Inspecter la base

```bash
docker exec -it pa5emeann-e-postgres-1 psql -U pawmatch -d pawmatch
```

Commandes utiles dans psql :
```sql
SELECT count(*) FROM animals;
SELECT name, species, source FROM animals LIMIT 10;
SELECT name, images FROM animals JOIN animal_images ON animals.id = animal_images.animal_id LIMIT 5;
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

Documentation interactive : http://localhost:8000/docs

---

## Développement sans Docker

Vraiment personnes fait ça la vie

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
DATABASE_URL=postgresql://pawmatch:pawmatch@localhost:5432/pawmatch python main_spa_full.py
```

**Modèle ML**
```bash
# Depuis la racine
pip install -r requirements.txt
python -m dl_models.data_pipeline.pet_dataset
python -m dl_models.train
```

---

## Variables d'environnement

Copier `.env.example` en `.env` et ajuster si besoin :

```bash
cp .env.example .env   # Linux/Mac
copy .env.example .env  # Windows
```

| Variable | Service | Description |
|----------|---------|-------------|
| `DATABASE_URL` | api, scraper | Connexion PostgreSQL |
| `API_URL` | front | URL interne de l'API (docker: `http://api:8000`) |
| `ALLOWED_ORIGINS` | api | CORS — origines autorisées |
| `SCRAPER_SOURCE` | scraper | Nom de la source scrapée |
| `MAX_PAGES` | scraper | Pages de listing à crawler |
| `NUM_WORKERS` | scraper | Workers Chrome parallèles |

Par défaut tout fonctionne sans modification pour le développement local avec Docker.

---

## CI / CD

Chaque push sur `main` déclenche un workflow GitHub Actions (`.github/workflows/ci.yml`) qui reconstruit les 3 images Docker (front, api, scraper) pour vérifier qu'aucune régression n'est introduite.

Le déploiement AWS (ECS + ECR + RDS) est préparé dans ce même fichier — commenté jusqu'à la configuration du compte cloud.

---

## Feuille de route cloud (AWS)

Quand on passera en production :

| Composant local | Équivalent AWS |
|-----------------|----------------|
| PostgreSQL Docker | RDS PostgreSQL + pgvector |
| Images Docker | ECR (Elastic Container Registry) |
| Conteneurs | ECS Fargate |
| Scraper ponctuel | EventBridge Scheduler → ECS Task |
| Images animaux | S3 + CloudFront |

Migration de la base : créer l'instance RDS, changer `DATABASE_URL`, relancer le scraper.  
Les données viennent de la-spa.fr — pas besoin de dump/restore.


## mention spécial à ClaudeCode sans qui rien de tout cela n'aurait été réalisable, je t'aime frérot je sais qu'un jour tu trouvera une Claudette gechar niveau GPU dans tout les cas moi je suis frérot tu peux faire croire je suis ton ptit frr handicapté vu comment t + smart que moi tkt les meufs elle vont kiff ton altruisme à la hauteur de la RAM que tu consomme mon bb