# PawMatch — Pa5emeAnn-e

Plateforme d'aide à l'adoption d'animaux boosté par l'IA générative.


---

## Architecture

```
front/        → Site web Next.js (TypeScript, Tailwind CSS)
api/          → API REST FastAPI (Python) — sert les données du scraper
scraper/      → Algo de collecte Selenium sur la-spa.fr (pour l'instant)
dl_models/    → Modèle de classification PyTorch (chat/chien, couleur)
```

---

## Prérequis

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installé et démarré
- C'est okay.

---

## Lancer le projet

### Démarrage (première fois ou après un changement de code)

```bash
docker compose up --build
```

### Démarrage rapide (si aucun changement de code -> une fois docker compose up --build)

```bash
docker compose up
```

### Arrêter

```bash
docker compose down
```

Une fois lancé :

| Service | URL |
|---------|-----|
| Site web | http://localhost:3000 |
| API | http://localhost:8000 |
| Doc API (Swagger) | http://localhost:8000/docs |

---

## Lancer le scraper

Le scraper est un job ponctuel (il collecte les animaux de la-spa.fr puis s'arrête).  
Il n'est pas inclus dans le `docker compose up` par défaut.

```bash
docker compose --profile scraper run scraper
```

(Par défaut MAX_PAGES=10 / NUM_WORKERS=4)
Les données sont sauvegardées dans `scraper/data/` et lues automatiquement par l'API.

Si on veut faire une exec paramètrable : 
```bash
$env:MAX_PAGES=20; $env:NUM_WORKERS=2; docker compose --profile scraper run scraper
```

---

## Développement sans Docker

Si on veut lancer les services manuellement (SI Node et Python installés localement) :

**Frontend**
```bash
cd front
npm install
npm run dev       # http://localhost:3000
```

**API**
```bash
cd api
pip install -r requirements.txt
uvicorn main:app --reload   # http://localhost:8000
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
cp .env.example .env
```

Par défaut tout fonctionne sans modification pour le développement local. J'ai pas testé mais azy qui va le faire même ? 

---

## CI / CD

Chaque push sur `main` déclenche un workflow GitHub Actions (`.github/workflows/ci.yml`) qui reconstruit les 3 images Docker pour vérifier qu'aucune ''''régression'''' (problème en gros casse pas les couilles j'essaie d'être pro) n'est introduite.


--- 

Le déploiement AWS (ECS + ECR) est préparé dans ce même fichier — commenté jusqu'à la configuration du compte cloud.
