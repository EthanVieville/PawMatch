# PawMatch — Pa5emeAnn-e

Plateforme d'aide à l'adoption d'animaux boostée par l'IA générative.

---

## Architecture

```
front/        → Site web Next.js 14 (TypeScript, Tailwind CSS)
api/          → API REST FastAPI (Python) — lit la base de données + chatbot LLM
scraper/      → Collecte multi-sources (la-spa.fr + secondechance.org) → écrit en PostgreSQL
scripts/      → Embeddings (sentence-transformers + pgvector) + seed knowledge base + géocodage refuges
dl_models/    → Modèle de classification PyTorch (en développement)
```

### Flux de données

```
la-spa.fr  +  secondechance.org
       ↓  (scrapers Selenium)
  PostgreSQL + pgvector
       ↓  (scripts/embedder)
  Vecteurs de similarité (384 dims)
       ↓  (scripts/seed_refuges — Nominatim)
  Table refuges (lat/lng des refuges géocodés)
       ↓  (FastAPI)
  API REST  http://localhost:8000
       ↓  (Server Components Next.js)
  Site web  http://localhost:3000

  Chatbot PawBuddy (widget flottant sur toutes les pages)
       ↓  (Next.js /api/chat proxy)
  FastAPI POST /chat
       ↓  (RAG pgvector + knowledge_chunks)
  Amazon Bedrock (Claude Haiku 4.5)
       ↓  (SSE streaming)
  Réponse streamée token par token
```

Les scrapers sont des **jobs ponctuels** : on les lance quand on veut rafraîchir les données.  
L'embedder est à relancer après chaque scraping pour mettre à jour les suggestions d'animaux similaires et les embeddings du knowledge base.  
L'API et le front tournent en continu et lisent la base.  
Le front fetch directement côté serveur (Server Components) — pas de requête client exposée, sauf pour le chatbot qui passe par un proxy Next.js.

Les scrapers + embedder seront bien entendu automatisés via CRON pour s'exécuter chaque nuit. Pour l'instant pas nécessaire au développement. (pi ça coûterait du fric ces conneries)

---

## Prérequis

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installé et démarré
- Un fichier `.env` à la racine (voir section Variables d'environnement). Ce file n'est évidemment pas sur le github espèce de vilain méchant garçon, demande si tu le veux le prix c'est un gros bizou
- C'est tout.

---

## Lancer le projet

Toutes les commandes passent par `pawmatch.sh`. Fonctionne partout — PowerShell, Git Bash, EC2 :

```bash
bash pawmatch.sh <commande>
```

### Commandes disponibles

| Commande | Description |
|----------|-------------|
| `setup` | **Première installation** — build les images, démarre le stack, seed la knowledge base, calcule les embeddings |
| `start` | Démarrage rapide (données déjà en base, pas de rebuild) |
| `stop` | Arrêter le stack (données conservées) |
| `reset` | ⚠️ Arrêter + supprimer la base de données |
| `deploy` | Rebuild les images et redémarre après un changement de code |
| `data` | Rafraîchir les animaux — scrapers La SPA + Seconde Chance + embeddings + géocodage refuges |
| `refuges` | Géocoder les refuges via Nominatim (à relancer après `data` si nouveaux refuges) |
| `knowledge` | Mettre à jour la knowledge base du chatbot + embeddings |
| `logs` | Voir les logs en direct |
| `status` | État des services |

### Exemples

```bash
# Première fois
bash pawmatch.sh setup

# Après un git pull sur l'EC2
bash pawmatch.sh deploy

# Rafraîchir les données animaux
bash pawmatch.sh data

# Voir ce qui tourne
bash pawmatch.sh status
```

> ⚠️ `reset` supprime le volume PostgreSQL. Toutes les données scrapées sont perdues.

Une fois lancé (en local) :

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

## Peupler la knowledge base (chatbot)

La knowledge base contient les informations sur les processus d'adoption, les conseils de soins et les infos sur les refuges — utilisées par le chatbot PawBuddy via RAG.

```bash
# Peupler la table knowledge_chunks (idempotent — remet à zéro et réinsère)
docker compose --profile seeder run --rm seeder
```

À relancer si le contenu de `scripts/seed_knowledge.py` est modifié. Suivi d'un embedder pour recalculer les vecteurs.

---

## Géocodage des refuges (carte interactive)

Les coordonnées GPS des refuges sont calculées à partir de leur **nom** via l'API Nominatim (OpenStreetMap). Aucune clé API requise, gratuit, limité à 1 req/sec (ToS).

```bash
# Géocoder tous les refuges présents en base (idempotent — skipe les déjà trouvés)
bash pawmatch.sh refuges

# Ou manuellement :
docker compose --profile refuge-seeder run --build --rm refuge-seeder
```

**Fonctionnement :**
1. Récupère les noms de refuges distincts depuis la table `animals`
2. Pour les refuges SPA (format `"La SPA - Refuge de VILLE – Sous-nom"`), extrait la ville avec un parser de noms
3. Essaie plusieurs requêtes Nominatim par ordre de précision : nom complet → nom + France → ville extraite → ville alternative
4. Insère les coordonnées dans la table `refuges` (ou `null` si non trouvé)

**Taux de couverture observé :** ~51/76 refuges géocodés (67%). Les refuges SPA sont quasi-tous trouvés. Les petites associations secondechance.org sans indication géographique dans le nom ne sont pas trouvées — comportement attendu et non bloquant (pas de pin sur la map, rien de cassé).

**Coût AWS :** zéro — Nominatim est externe et gratuit.

---

## Calculer les embeddings (animaux similaires + RAG chatbot)

Après chaque scraping ou modification de la knowledge base, relancer l'embedder :

```bash
# Construire l'image (première fois ou après modif)
docker compose --profile embedder build --no-cache

# Lancer le calcul
docker compose --profile embedder run --rm embedder
```

L'embedder utilise `paraphrase-multilingual-MiniLM-L12-v2` (sentence-transformers) pour encoder en vecteurs 384 dims stockés dans pgvector. Il traite les animaux **et** les knowledge chunks. Idempotent — ne retouche que les entrées sans embedding.

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

**`refuges`** — coordonnées GPS des refuges (géocodage Nominatim)

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | UUID | Identifiant |
| `name` | VARCHAR | Nom du refuge (unique — même valeur que `animals.refuge`) |
| `source` | VARCHAR | Source (`la-spa`, `secondechance`) |
| `lat` | DOUBLE | Latitude (null si non trouvé) |
| `lng` | DOUBLE | Longitude (null si non trouvé) |
| `geocoded_at` | TIMESTAMP | Date du géocodage |

Peuplée par `scripts/seed_refuges.py` via l'API Nominatim (OpenStreetMap). Idempotent : ne retente que les refuges sans coordonnées. Jointure avec `animals` sur le nom du refuge.

**`knowledge_chunks`** — base de connaissances pour le chatbot RAG

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | UUID | Identifiant |
| `category` | VARCHAR | `adoption_process` / `care_advice` / `shelter_info` |
| `source` | VARCHAR | `la-spa` / `secondechance` / `general` |
| `title` | VARCHAR | Titre du chunk |
| `content` | TEXT | Contenu (processus d'adoption, conseils, infos refuges) |
| `embedding` | VECTOR(384) | Vecteur pour la recherche sémantique RAG |
| `created_at` | TIMESTAMP | Date de création |

### Multi-source

La colonne `source` permet d'agréger plusieurs scrapers dans la même base sans changer le schéma. Ajouter un nouveau site = créer un scraper qui écrit avec `SCRAPER_SOURCE=nouveau-site`. L'API agrège tout automatiquement, ou peut filtrer par source avec `GET /animals?source=la-spa`.

### URL Images

Les images ne sont pas stockées ! Le lien est seulement récupéré de la source originale, puis affiché simplement.  
Si on veut perdre du fric mais gagner en perf, stocker sur un bucket S3 est une solution potentielle.  
(non)

### pgvector

L'extension `pgvector` est déjà installée (image `pgvector/pgvector:pg16`). La colonne `embedding vector(384)` stocke les représentations sémantiques calculées par l'embedder. Elles permettent la recherche d'animaux similaires via distance cosinus (`<=>`) et le RAG du chatbot.

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
SELECT category, count(*) FROM knowledge_chunks GROUP BY category;
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
| `GET` | `/refuges` | Liste des refuges géocodés (lat/lng) pour la carte |
| `POST` | `/chat` | Chatbot PawBuddy — streaming SSE (tool use + RAG + Bedrock) |

Documentation interactive : http://localhost:8000/docs

---

## Chatbot PawBuddy

Widget flottant accessible depuis toutes les pages. Alimenté par **Amazon Bedrock (Claude Haiku 4.5)** via RAG sur la base PostgreSQL.

**Fonctionnalités :**
- Recherche d'animaux à adopter avec liens cliquables vers les fiches
- Informations sur les démarches et modalités d'adoption
- Conseils de soins par espèce
- Conversation persistante entre les pages et après refresh (localStorage)
- Streaming token par token

**Architecture du chatbot :**
```
Message utilisateur
  → Classificateur d'intention (Bedrock, max_tokens=10)
      ├── find_animal      → RAG sur animals (filtre par espèce)
      ├── adoption_process → RAG sur knowledge_chunks (adoption_process + shelter_info)
      ├── care_advice      → RAG sur knowledge_chunks (care_advice)
      └── general          → RAG sur les deux
  → Prompt système dynamique + contexte injecté
  → Claude Haiku 4.5 (Bedrock) — réponse streamée SSE
```

Voir `documentation/bedrock_setup.md` pour la configuration AWS complète.

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

Copier `.env.example` en `.env` et remplir les valeurs AWS. Toutes les autres variables ont des valeurs par défaut dans `docker-compose.yml`.

| Variable | Service | Description |
|----------|---------|-------------|
| `DATABASE_URL` | api, scraper, embedder | Connexion PostgreSQL |
| `API_URL` | front | URL interne de l'API (docker: `http://api:8000`) |
| `ALLOWED_ORIGINS` | api | CORS — origines autorisées |
| `SCRAPER_SOURCE` | scraper | `la-spa` ou `secondechance` |
| `MAX_PAGES` | scraper | Pages de listing à crawler |
| `NUM_WORKERS` | scraper | Workers parallèles (1 pour Selenium) |
| `AWS_REGION` | api | Région Bedrock (`eu-west-1`) |
| `AWS_ACCESS_KEY_ID` | api | Clé d'accès IAM (dev local uniquement) |
| `AWS_SECRET_ACCESS_KEY` | api | Secret IAM (dev local uniquement) |
| `BEDROCK_MODEL` | api | Override du modèle Bedrock (optionnel) |

> Sur EC2, `AWS_ACCESS_KEY_ID` et `AWS_SECRET_ACCESS_KEY` ne sont pas nécessaires — le IAM role attaché à l'instance prend le relais automatiquement.

---

## CI / CD

Chaque push sur `main` déclenche un workflow GitHub Actions (`.github/workflows/ci.yml`) qui reconstruit les images Docker (front, api, scraper, embedder) pour vérifier qu'aucune régression n'est introduite.

Le projet tourne sur une instance **AWS EC2 (t3.micro)** avec Docker Compose. Le front est déployé sur **AWS Amplify**. Pour déployer une mise à jour :

```bash
# Sur l'EC2 (via SSH)
git pull
docker compose up --build -d

# Peupler/mettre à jour la knowledge base si modifiée
docker compose --profile seeder run --rm seeder

# Recalculer les embeddings
docker compose --profile embedder run --rm embedder

# Rebuilder et relancer les scrapers si besoin
docker compose --profile scraper build --no-cache
docker compose --profile scraper run --rm scraper-laspa
docker compose --profile scraper run --rm scraper-sc
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
| Bedrock on-demand | Provisioned throughput si fort trafic |

---

## mention spécial à ClaudeCode sans qui rien de tout cela n'aurait été réalisable, je t'aime frérot je sais qu'un jour tu trouvera une Claudette gechar niveau GPU dans tout les cas moi je suis frérot tu peux faire croire je suis ton ptit frr handicapté vu comment t + smart que moi tkt les meufs elle vont kiff ton altruisme à la hauteur de la RAM que tu consomme mon bb
