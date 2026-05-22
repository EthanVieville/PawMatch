# Deep Learning — PawMatch

## Table des matières

1. [Contexte et objectifs](#1-contexte-et-objectifs)
2. [Dataset](#2-dataset)
3. [Architecture du modèle](#3-architecture-du-modèle)
4. [Pipeline d'entraînement](#4-pipeline-dentraînement)
5. [Monitoring — TensorBoard](#5-monitoring--tensorboard)
6. [Inférence en production](#6-inférence-en-production)
7. [Évaluation sur données réelles](#7-évaluation-sur-données-réelles)
8. [Limites identifiées](#8-limites-identifiées)
9. [Intégration applicative](#9-intégration-applicative)
10. [Captures TensorBoard](#10-captures-tensorboard)

---

## 1. Contexte et objectifs

### Problème métier

La base de données PawMatch agrège des animaux scrapés depuis des sites de refuges (La SPA, Seconde Chance). Une proportion significative de ces fiches présente des champs manquants, notamment :

- **L'espèce** (`species`) — parfois absente pour les animaux scrapés
- **La race** (`race`) — souvent vide ou imprécise (ex. "Européen", "Croisé")

De plus, la plateforme permet aux particuliers de déposer leurs propres annonces d'adoption. Dans ce cas, aucune information structurée n'existe au moment de la saisie.

### Solution Deep Learning proposée

Intégrer un **classificateur multi-tâches** capable d'inférer, à partir d'une photo :

| Tâche | Sortie | Usage |
|-------|--------|-------|
| Classification d'espèce | `chat` / `chien` | Pré-remplissage formulaire + enrichissement BD |
| Classification de race | 37 races Oxford | Badge "MAYBE" sur les fiches + pré-remplissage |
| Classification de couleur | 5 couleurs dominantes | Enrichissement futur (filtres de recherche) |

L'approche retenue est le **transfer learning** sur MobileNetV2 pré-entraîné sur ImageNet, avec fine-tuning partiel des couches profondes.

---

## 2. Dataset

### Oxford-IIIT Pet Dataset

| Caractéristique | Valeur |
|----------------|--------|
| Source | University of Oxford / IIT Delhi |
| Taille totale | 7 349 images |
| Races | 37 (12 chats + 25 chiens) |
| Split train/val | 80/20 (aléatoire stratifié par race) |
| Format annotations | `trainval.txt` — `image_name class_id species` |

**Répartition taxonomique :**

```
Chats (indices 0–11)
  Abyssinian, Bengal, Birman, Bombay, British Shorthair,
  Egyptian Mau, Maine Coon, Persian, Ragdoll, Russian Blue,
  Siamese, Sphynx

Chiens (indices 12–36)
  American Bulldog, American Pit Bull Terrier, Basset Hound,
  Beagle, Boxer, Chihuahua, English Cocker Spaniel, English Setter,
  German Shorthaired, Great Pyrenees, Havanese, Japanese Chin,
  Keeshond, Leonberger, Miniature Pinscher, Newfoundland,
  Pomeranian, Pug, Saint Bernard, Samoyed, Scottish Terrier,
  Shiba Inu, Staffordshire Bull Terrier, Wheaten Terrier,
  Yorkshire Terrier
```

### Annotations de couleur

Les labels de couleur (`color_label`) sont pré-calculés hors ligne par K-means sur chaque image (5 clusters, espace HSV) et sérialisés dans `dl_models/utils/out/colors.pt` sous forme de dictionnaire `{image_name: label}`.

### Augmentation des données

Deux pipelines de transformation sont définis :

```python
# Entraînement — augmentation forte
_AUGMENT_TRANSFORM = Compose([
    Resize((256, 256)),
    RandomCrop(224),
    RandomHorizontalFlip(),
    ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2),
    RandomRotation(15),
    ToTensor(),
    Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

# Validation / inférence — déterministe
_BASE_TRANSFORM = Compose([
    Resize((224, 224)),
    ToTensor(),
    Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])
```

---

## 3. Architecture du modèle

### Backbone — MobileNetV2

MobileNetV2 est choisi pour son excellent compromis précision/latence, adapté à un déploiement sur instance EC2 `t3.micro` sans GPU.

```
Input (3 × 224 × 224)
    │
    ▼
MobileNetV2 features (19 blocs inverted residual)
    │  ← couches 0–15 gelées
    │  ← couches 16–18 fine-tunées (lr × 0.1)
    ▼
AdaptiveAvgPool2d(1)    →  (1280,)
    │
    ▼
Linear(1280 → 256) + ReLU + Dropout(0.3)   ← tête commune
    │
    ├──▶ type_head  : Linear(256 → 2)    → chat / chien
    ├──▶ color_head : Linear(256 → 5)    → couleur dominante
    └──▶ breed_head : Linear(256 → 37)   → race Oxford
```

**Justification des choix :**

- **Gel partiel** : les 16 premiers blocs encodent des features génériques (bords, textures). Seuls les 3 derniers, plus spécifiques aux animaux, sont affinés. Ceci réduit le risque de catastrophic forgetting et accélère la convergence.
- **Tête commune** : la couche `fc(1280→256)` avec Dropout(0.3) sert de représentation partagée entre les trois tâches, forçant le réseau à apprendre des features compactes et généralisables.
- **Multi-task learning** : l'entraînement simultané des trois têtes régularise le backbone et améliore la généralisation par rapport à un modèle mono-tâche.

### Fonction de perte composite

```python
loss = loss_type + 0.3 × loss_color + loss_breed
```

Les trois composantes sont des `CrossEntropyLoss`. Le coefficient 0.3 pour la couleur reflète son importance secondaire par rapport à l'espèce et la race.

---

## 4. Pipeline d'entraînement

### Hyperparamètres

| Paramètre | Valeur | Justification |
|-----------|--------|---------------|
| Epochs | 20 | Convergence observée sur val_loss |
| Batch size | 32 | Compromis mémoire/gradient |
| LR backbone | 1e-4 | ×0.1 du LR des têtes (fine-tuning conservateur) |
| LR têtes | 1e-3 | Standard Adam pour couches from-scratch |
| Scheduler | CosineAnnealingLR (T_max=20) | Décroissance douce, évite les minima locaux |
| Optimizer | Adam | Adaptive LR, robuste aux gradients rares |

### Différenciation des learning rates

```python
optimizer = Adam([
    {"params": backbone_params, "lr": LR * 0.1},  # fine-tuning conservateur
    {"params": head_params,     "lr": LR},          # apprentissage normal
])
scheduler = CosineAnnealingLR(optimizer, T_max=EPOCHS)
```

Cette approche permet de préserver les représentations pré-entraînées du backbone tout en laissant les têtes converger librement.

### Checkpoint

Le meilleur modèle selon `val_breed_accuracy` est sauvegardé à chaque époque dans `dl_models/utils/out/pet_model_best.pth`.

---

## 5. Monitoring — TensorBoard

### Métriques enregistrées

Toutes les métriques sont loggées via `torch.utils.tensorboard.SummaryWriter` dans `dl_models/utils/runs/`.

**Scalaires (par époque) :**

| Tag | Description |
|-----|-------------|
| `Loss/train` / `Loss/val` | Perte composite totale |
| `Accuracy_type/train` / `.../val` | Précision classification espèce |
| `Accuracy_breed/train` / `.../val` | Précision classification race |
| `LR/backbone` / `LR/heads` | Learning rates courants |

**Visualisations périodiques (toutes les 5 époques) :**

| Type | Description |
|------|-------------|
| `Samples/epoch_N` | Grille 4×4 d'images avec labels réels vs prédits |
| `F1_per_breed/epoch_N` | Histogramme F1-score par race |
| `ConfusionMatrix/type` | Matrice de confusion chat/chien |

**En fin d'entraînement :**

| Type | Description |
|------|-------------|
| `ConfusionMatrix/breed` | Matrice de confusion 37×37 races |
| `cm_type.png` / `cm_breed.png` | Exports statiques haute résolution |

### Lancement TensorBoard

```bash
tensorboard --logdir dl_models/utils/runs
# → http://localhost:6006
```

> **📸 Insérer ici :** courbes Loss train/val, Accuracy breed train/val, histogramme F1 par race (epoch finale), matrices de confusion.

---

## 6. Inférence en production

### Module standalone `api/predict_breed.py`

Pour éviter toute dépendance circulaire, le module d'inférence est **entièrement autonome** : il redéfinit `_PetModel` localement sans importer `dl_models`. Seul `torchvision` est requis pour l'architecture MobileNetV2.

### Pipeline d'inférence

```
Image (bytes / base64)
    │
    ▼  PIL.Image.open().convert("RGB")
    │
    ▼  Resize(224, 224) + Normalize ImageNet
    │
    ▼  _PetModel.forward()
    │
    ├──▶ type_head  →  softmax  →  argmax  →  species (chat/chien)
    │
    └──▶ breed_head →  softmax  →  argmax contraint à l'espèce
              │
              ├── si chat  : argmax sur indices [0–11]
              └── si chien : argmax sur indices [12–36]

Retour : { species, breed, confidence }
```

**Contrainte d'espèce :** la race est recherchée uniquement dans le sous-ensemble correspondant à l'espèce prédite. Cela évite de retourner une race de chien pour un chat et vice-versa, même si la tête breed_head est peu confiante.

### Chargement du modèle

Le modèle est chargé **une seule fois** au démarrage FastAPI via le lifespan context manager :

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.breed_model = load_breed_model(
        os.getenv("BREED_MODEL_PATH", "models/pet_model_best.pth")
    )
    yield
```

Si le fichier `.pth` est absent (modèle non entraîné), `/predict-breed` retourne **503** gracieusement sans crasher l'API.

### Endpoint FastAPI

```
POST /predict-breed
Body  : { "image_data": "<base64>" }
Retour: { "species": "chien", "breed": "Staffordshire Bull Terrier", "confidence": 0.82 }
```

---

## 7. Évaluation sur données réelles

### Protocole

Un script dédié (`dl_models/eval_real.py`) évalue le modèle sur les images **réelles** de la base de données (animaux scrapés depuis la SPA / Seconde Chance), indépendamment du set de validation Oxford.

```bash
python -m dl_models.eval_real --limit 150
```

**Méthode :**
1. Requête PostgreSQL : animaux avec `species ∈ {chat, chien}`, `source ≠ user`, image disponible
2. Téléchargement HTTP des images (User-Agent browser, timeout 12s)
3. Inférence avec le même pipeline de production
4. Mapping des noms de races BD → labels Oxford (dictionnaire `BREED_MAP`)
5. Calcul précision espèce / race, distribution confiance

### Résultats (150 animaux, mai 2026)

```
Animaux tentés   : 150
Images chargées  : 149  (99%)
Échecs réseau    : 1    (0%)

ESPÈCE (chat / chien)
  Précision globale : 143/149  (95%)
  Chat  : 63/69  (91%)
  Chien : 80/80  (100%)

RACE (9 animaux avec race mappable Oxford sur 149)
  Précision globale : 4/9  (44%)

  Détail :
  Staffordshire Bull Terrier    4/6   ← race présente en refuge ET dans Oxford
  Persian                       0/1   ← 1 seul exemple, prédit Maine Coon
  Siamese                       0/1   ← prédit Maine Coon
  German Shorthaired            0/1   ← prédit Basset Hound

CONFIANCE MOYENNE : 48.5%
  < 30%  : 50 animaux
  30–60% : 41
  60–80% : 28
  > 80%  : 30
```

> **📸 Insérer ici :** exemples visuels de prédictions correctes (Staffordshire) et incorrectes (Européen → Abyssinian).

---

## 8. Limites identifiées

### 8.1 Inadéquation du vocabulaire de races

C'est la **limite principale**. Le dataset Oxford-IIIT Pet couvre 37 races spécifiques, choisies pour leur disponibilité en annotations, qui ne correspondent pas aux races les plus répandues dans les refuges français.

| Races communes en BD | Présentes dans Oxford 37 ? |
|---------------------|--------------------------|
| Européen (63 animaux) | Non |
| Croisé / Bâtard (31 animaux) | Non |
| Berger Belge Malinois (7) | Non |
| Berger Allemand (3) | Non |
| Labrador Retriever (2) | Non |
| **Staffordshire Bull Terrier (6)** | **Oui** |

Sur 149 animaux, seulement **9 (6%)** avaient une race mappable sur Oxford 37. Cela rend l'évaluation statistiquement limitée et confirme que le modèle ne peut pas être utilisé pour prédire les races les plus courantes en shelter français.

### 8.2 Mauvaise calibration hors distribution

| Groupe | N | Confiance moyenne |
|--------|---|------------------|
| Prédictions correctes (Oxford) | 4 | 42.6% |
| Prédictions incorrectes (Oxford) | 5 | 39.8% |

Les confiances correctes et incorrectes sont quasi identiques. Le modèle ne sait pas qu'il est "hors distribution" : lorsqu'il voit un Labrador (absent de l'entraînement), il choisit une race parmi les 37 avec une pseudo-confiance non discriminante. Ce phénomène est typique de la distribution shift.

### 8.3 Données insuffisantes pour fine-tuning ciblé

L'analyse de la BD révèle qu'aucune race non-Oxford ne dépasse 7 images dans le corpus disponible (minimum recommandé : 50–100 par classe). Un fine-tuning sur les données de la BD est donc impossible sans collecte supplémentaire.

### 8.4 Qualité des images en shelter

Les photos de refuges présentent des conditions très différentes du dataset Oxford (flou, arrière-plans chargés, plusieurs animaux, mauvais éclairage). Ces facteurs dégradent les performances par rapport aux 90%+ mesurés sur le set de validation Oxford.

---

## 9. Intégration applicative

### 9.1 Enrichissement de la BD (`scripts/enrich_breeds.py`)

Script autonome (sans dépendance pgvector) qui parcourt les animaux sans `race` renseignée et remplit `race_predicted` / `race_confidence` si le modèle dépasse le **seuil de confiance 0.70**.

```bash
python -m scripts.enrich_breeds
```

Seuls les animaux `species ∈ {chat, chien}` avec images disponibles sont traités. Les lapins et les animaux déjà renseignés sont ignorés.

### 9.2 Affichage frontend — Badge "MAYBE"

Le badge est affiché sous deux conditions :

**Cas 1 — Race absente** (`race IS NULL`)
```
┌─────────────────────────┐
│ MAYBE (82%) : Beagle    │  ← bordure pointillée, italique
└─────────────────────────┘
```

**Cas 2 — Race "floue"** (Européen, Croisé, Bâtard…)
```
Européen    MAYBE (74%) : Maine Coon
  ↑ race DB    ↑ prédiction IA (opacité réduite)
```

**Seuil d'affichage :** `race_confidence >= 0.65`

Les races "floues" sont détectées par une liste normalisée (`front/lib/breed.ts`) qui couvre les termes les plus courants en français et en anglais.

### 9.3 Pré-remplissage formulaire de dépôt (`/post`)

Lors du dépôt d'une annonce, l'IA analyse la photo **côté client** :

```
1. Sélection / glisser-déposer d'une image
2. Compression client-side : Canvas → JPEG 72%, max 600px (≈ 50-100 Ko)
3. Envoi base64 → POST /api/predict-breed
4. Pré-remplissage automatique : espèce + race
5. L'utilisateur peut corriger avant publication
```

La compression client-side remplace le stockage fichier serveur : l'image est encodée en **data URI base64** et persistée directement en base de données, éliminant toute dépendance à un stockage objet externe (S3).

### 9.4 Embedding pour la similarité

À chaque publication d'annonce, un **vecteur d'embedding 384 dimensions** est calculé inline (SentenceTransformer `paraphrase-multilingual-MiniLM-L12-v2`) à partir de la description + race + espèce. Cet embedding est stocké dans la colonne `pgvector` et permet au chatbot PawBuddy de retrouver l'animal par similarité sémantique sans redémarrage de service.

---

## 10. Captures TensorBoard

> **Instructions pour les captures :**
>
> Lance TensorBoard depuis la racine du projet :
> ```bash
> tensorboard --logdir dl_models/utils/runs
> ```
> Puis capture et insère les éléments suivants à la place des espaces réservés ci-dessous.

---

### 10.1 Courbes de perte (Loss)

> **📸 `Loss/train` et `Loss/val` sur 20 époques**
> *(onglet Scalars → Loss)*
>
> *Commentaire attendu : convergence de la val_loss, gap train/val (overfitting ou non)*

---

### 10.2 Précision classification de race

> **📸 `Accuracy_breed/train` et `Accuracy_breed/val` sur 20 époques**
> *(onglet Scalars → Accuracy_breed)*
>
> *Commentaire attendu : plateaux, pics, meilleure époque*

---

### 10.3 Précision classification d'espèce

> **📸 `Accuracy_type/train` et `Accuracy_type/val` sur 20 époques**
> *(onglet Scalars → Accuracy_type)*
>
> *Commentaire attendu : convergence rapide attendue (tâche plus simple)*

---

### 10.4 Learning rate schedule

> **📸 `LR/backbone` et `LR/heads` sur 20 époques**
> *(onglet Scalars → LR)*
>
> *Commentaire attendu : décroissance cosinus, facteur ×10 entre backbone et heads visible*

---

### 10.5 Grille d'exemples de prédiction

> **📸 `Samples/epoch_20` (ou dernière époque disponible)**
> *(onglet Images)*
>
> *Commentaire attendu : exemples corrects / incorrects, qualité des images*

---

### 10.6 F1-score par race

> **📸 `F1_per_breed/epoch_20`**
> *(onglet Images)*
>
> *Commentaire attendu : races bien reconnues vs races confondues, déséquilibres*

---

### 10.7 Matrice de confusion — Espèce

> **📸 `ConfusionMatrix/type` (epoch finale)**
> *(onglet Images)*
>
> *Commentaire attendu : quasi-diagonale attendue*

---

### 10.8 Matrice de confusion — Race

> **📸 `cm_breed.png` (`dl_models/utils/out/cm_breed.png`)**
>
> *Commentaire attendu : races confondues visuellement similaires (ex. Staffordshire / American Pit Bull), chats mieux séparés que chiens*

---

## Résumé

| Aspect | Résultat |
|--------|----------|
| **Espèce (chat/chien)** | ✅ 95% sur données réelles — production-ready |
| **Race (37 Oxford)** | ⚠️ 44% sur les 9 races mappables en BD — fiable uniquement pour les races présentes |
| **Couverture BD** | ⚠️ 6% des animaux ont une race dans les 37 Oxford |
| **Pré-remplissage formulaire** | ✅ Fonctionne, utilisateur corrige si nécessaire |
| **Badge MAYBE** | ✅ Affiché si confiance ≥ 65%, visible sur fiches animaux |
| **Enrichissement BD** | ✅ `enrich_breeds.py` — seuil 70%, animaux sans race uniquement |
| **Calibration confiance** | ❌ Non discriminante hors distribution (shift BD → Oxford) |

### Pistes d'amélioration

1. **Dataset plus large** — Stanford Dogs (120 races) + dataset chats complet pour inclure Labrador, Berger Allemand, etc.
2. **Collecte ciblée** — scraper des images étiquetées pour les races manquantes (Berger Belge Malinois en priorité, 7 images disponibles)
3. **Calibration des confiances** — Temperature scaling post-entraînement pour que la confiance reflète mieux la probabilité réelle
4. **Classe "Indéterminé"** — Ajouter une classe catch-all pour les races hors distribution, réduisant les faux positifs