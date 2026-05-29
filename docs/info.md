# Nyaya — Documentation

## Table des matières

1. [Prérequis](#1-prérequis)
2. [Démarrage](#2-démarrage)
3. [Gestion des dépendances](#3-gestion-des-dépendances)
4. [Base de données](#4-base-de-données)
5. [Architecture](#5-architecture)
6. [Core](#6-core)
7. [Variables d'environnement](#7-variables-denvironnement)
8. [Tests](#8-tests)
9. [Mise en production](#9-mise-en-production)

---

## 1. Prérequis

- **Python 3.12+**
- **Make** — Windows : [GnuWin32](http://gnuwin32.sourceforge.net/packages/make.htm) ou via Git Bash / WSL
- **Docker Desktop**

---

## 2. Démarrage

### 2.1. Premier lancement

```bash
# 1. Copier le fichier d'environnement et renseigner les valeurs
cp .env.example .env

# 3. Setup complet (venv, docker, dépendances, migrations)
make setup
```

`make setup` crée le virtualenv, compile et installe les dépendances, puis applique les migrations.

### 2.2. Lancement quotidien

```bash
make dev
```

Démarre le serveur FastAPI en mode dev (hot-reload) et le worker Taskiq.

### 2.3. Après un pull

```bash
make sync
```

Recompile les dépendances si les `.in` ont changé, met à jour le venv, et applique les nouvelles migrations.

---

## 3. Gestion des dépendances

On utilise **pip-tools** avec **uv** pour séparer et verrouiller les dépendances.

### 3.1. Fichiers source

| Fichier | Rôle |
| --- | --- |
| `requirements.in` | Dépendances de production |
| `requirements-dev.in` | Dépendances de dev (inclut prod via `-r requirements.in`) |
| `requirements.txt` | Lockfile prod (généré, ne pas éditer) |
| `requirements-dev.txt` | Lockfile dev (généré, ne pas éditer) |

Le `-r requirements.in` dans le fichier dev garantit que les versions sont résolues ensemble — pas de conflit possible entre prod et dev.

### 3.2. Ajouter un package

1. Ajouter la dépendance dans le bon fichier `.in` :
   - prod → `requirements.in`
   - dev uniquement → `requirements-dev.in`
2. Spécifier une contrainte de version si nécessaire : `fastapi>=0.115,<0.116`
3. Appliquer :

```bash
make sync
```

### 3.3. Mettre à jour un package

<!-- #TODO -->

---

## 4. Base de données

### 4.1. Modèles

Approche **code-first**. Les modèles SQLAlchemy sont dans `src/app/modules/{module}/model.py`. Modifier la table = modifier le modèle, puis générer une migration.

### 4.2. Migrations

```bash
# Générer une migration après avoir modifié un modèle
make revision msg="description_courte"

# Appliquer les migrations en attente
make migrate

# Annuler la dernière migration
make migrate-down

# Reset complet de la DB (DEV uniquement — irréversible)
make db-reset
```

---

## 5. Architecture

### 5.1. Arborescence

```txt
nyaya/
├── .env.example
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── pyproject.toml
├── requirements.in
├── requirements-dev.in
├── requirements.txt              (généré)
├── requirements-dev.txt          (généré)
│
├── docs/
│   └── info.md
│
├── migrations/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│
├── scripts/
│   └── seed.py
│
├── tests/
│   ├── conftest.py
│   └── ai/
│
└── src/app/
    ├── main.py                   # Factory FastAPI, lifespan, middlewares, handlers
    │
    ├── background/               # Tâches asynchrones (Taskiq)
    │   └── tasks/
    │       └── review.py
    │
    ├── scheduler/                # Tâches planifiées (APScheduler)
    │   └── jobs/
    │
    ├── core/                     # Infrastructure transverse (voir §6)
    │   ├── api/
    │   │   ├── router.py
    │   │   ├── dependencies/
    │   │   │   ├── auth.py
    │   │   │   ├── db.py
    │   │   │   └── request_id.py
    │   │   └── v1/
    │   │       ├── router.py
    │   │       ├── evaluations.py
    │   │       ├── messages.py
    │   │       ├── totems.py
    │   │       └── users.py
    │   ├── config/
    │   │   ├── settings.py
    │   │   ├── database.py
    │   │   ├── redis.py
    │   │   ├── broker.py
    │   │   └── logs.py
    │   ├── errors/
    │   │   ├── exceptions/
    │   │   └── handlers/
    │   ├── middleware/
    │   ├── security/
    │   └── utils/
    │
    └── modules/                  # Domaines métier
        ├── base/                 # Modèle et schémas de base partagés
        ├── users/
        ├── messages/
        ├── evaluations/
        ├── feedbacks/
        ├── totems/
        ├── user_totems/
        └── llm/
            ├── connectors/       # Ollama, Mistral...
            └── evaluation/       # Framework d'évaluation LLM
```

### 5.2. Anatomie d'un module — de la route à la DB

Chaque module suit la même structure en 5 fichiers :

```txt
modules/{module}/
├── model.py          # Entité SQLAlchemy
├── schemas.py        # Schémas Pydantic (requête / réponse)
├── exceptions.py     # Exceptions métier du module
├── repository.py     # Accès base de données
├── service.py        # Logique métier
└── dependencies.py   # Injection de dépendances (factories)
```

**Le flux d'une requête :**

```txt
Router (core/api/v1/) → Dependencies → Service → Repository → Model
```

---

**`model.py`** — l'entité SQLAlchemy, définit la table et les relations :

```python
class User(Base):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(unique=True)
```

---

**`schemas.py`** — les schémas Pydantic, un par usage :

- **Request** : validation des entrées + `to_model()` pour convertir vers le modèle SQLAlchemy
- **Response** : `from_model()` (classmethod) pour sérialiser + `ConfigDict(from_attributes=True)`
- **Update** : tous les champs optionnels, utilise `model_dump(exclude_unset=True)` pour ne toucher que ce qui est fourni

---

**`exceptions.py`** — les erreurs métier du module :

```python
class UserNotFoundException(AppException):
    def __init__(self):
        super().__init__(status_code=404, message="User not found", tag="USER")
```

Héritent de `AppException` (définie dans `core/errors/exceptions/base.py`). Un handler centralisé les transforme automatiquement en réponse HTTP cohérente.

---

**`repository.py`** — les requêtes SQL, rien d'autre :

```python
class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
```

---

**`service.py`** — la logique métier, orchestre le repo via l'UoW :

```python
class UserService:
    def __init__(self, uow: UnitOfWork, ...):
        self.uow = uow

    async def get(self, user_id: UUID) -> UserResponse:
        async with self.uow:
            user = await self.uow.users.get_by_id(user_id)
            if not user:
                raise UserNotFoundException()
            return UserResponse.from_model(user)
```

L'UoW (`core/api/dependencies/uow.py`) centralise la session DB et les repositories. Il commite ou rollback automatiquement à la sortie du `async with`.

---

**`dependencies.py`** — câble le service et cache la complexité :

```python
def get_user_service(
    uow: UnitOfWork = Depends(get_uow),
    current_user: User = Depends(get_current_user),
) -> UserService:
    return UserService(uow, current_user)
```

---

**`core/api/v1/{module}.py`** — le router, aussi simple que possible :

```python
@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    service: UserService = Depends(get_user_service),
):
    return await service.get(user_id)
```

Aucune logique dans le router. Toute la complexité (DB, auth, logging) est dans les dependencies.

---

## 6. Core

Infrastructure transverse, partagée par tous les modules.

**`core/config/`** — configuration centralisée via Pydantic Settings. Les variables d'environnement sont lues depuis `.env` et validées au démarrage. `database.py` configure l'engine SQLAlchemy async, `redis.py` la connexion Redis, `broker.py` le broker Taskiq.

**`core/errors/`** — gestion centralisée des erreurs :

- `exceptions/base.py` — `AppException` (base de toutes les erreurs métier)
- `handlers/business.py` — intercepte les `AppException` → réponse HTTP structurée
- `handlers/db.py` — intercepte les erreurs SQLAlchemy (violation de contrainte unique, etc.)
- `handlers/catchall.py` — filet de sécurité, transforme toute exception imprévue en 500

**`core/middleware/`** :

- `headers.py` — injecte les headers de sécurité et le `X-Request-ID` sur chaque réponse
- `rate_limit.py` — limitation de débit par IP via Redis

**`core/api/dependencies/`** :

- `auth.py` — validation du JWT, récupère l'utilisateur courant
- `db.py` — fournit la session SQLAlchemy async par requête
- `request_id.py` — génère un UUID unique par requête pour la traçabilité

**`core/security/`** :

- `hash_lib.py` — hachage et vérification des mots de passe (argon2/bcrypt)
- `anonymize_lib.py` — anonymisation des données sensibles pour les logs

---

## 7. Variables d'environnement

Toutes les variables sont lues depuis `.env` (copié depuis `.env.example`) et validées au démarrage par Pydantic Settings. Un démarrage échoue immédiatement si une variable obligatoire est absente ou invalide.

### Base de données (PostgreSQL)

| Variable | Exemple | Rôle |
| --- | --- | --- |
| `DB_HOST` | `localhost` | Adresse du serveur PostgreSQL |
| `DB_PORT` | `5432` | Port TCP |
| `DB_NAME` | `nyaya_db` | Nom de la base |
| `DB_USER` | `nyaya_user` | Utilisateur PostgreSQL |
| `DB_PASSWORD` | *(secret)* | Mot de passe — générer avec `openssl rand -hex 64` |

En dev, PostgreSQL tourne via Docker Compose. En production, `DB_HOST` pointe vers un service managé (RDS, Cloud SQL…) injecté par l'orchestrateur.

### Redis

| Variable | Exemple | Rôle |
| --- | --- | --- |
| `REDIS_HOST` | `localhost` | Adresse du serveur Redis |
| `REDIS_PORT` | `6379` | Port TCP |
| `REDIS_PASSWORD` | *(secret)* | Mot de passe — générer avec `openssl rand -hex 64` |

Redis sert à deux choses : la **limitation de débit** par IP (middleware) et le **broker Taskiq** pour les tâches d'évaluation LLM asynchrones.

### Clé API (`API_KEY`)

```env
API_KEY=<hex 64 octets>   # openssl rand -hex 64
```

C'est la clé partagée que le **backend appelant** (le réseau social) doit envoyer dans chaque requête via le header `X-API-Key`. Sans ce header valide, toutes les routes renvoient `401`. Elle protège l'ensemble de l'API `/api/v1/`.

### LLM

| Variable | Exemple | Rôle |
| --- | --- | --- |
| `LLM_BASE_URL` | `http://localhost:11434` | URL de base de l'API LLM |
| `LLM_MODEL` | `gemma4:e2b` | Nom du modèle à utiliser |
| `LLM_API_KEY` | *(secret)* | Clé d'API pour un fournisseur distant (Mistral, OpenAI…) |
| `LLM_TIMEOUT_SECONDS` | `60` | Délai max d'attente d'une réponse LLM (10–300 s) |
| `LLM_USE_MOCK` | `false` | `true` = stubs aléatoires, aucun appel LLM réel (utile pour les tests) |

Deux modes de fonctionnement :

- **Local (Ollama)** — `LLM_BASE_URL=http://localhost:11434`, `LLM_API_KEY` ignorée, modèle local (ex. `gemma4:e2b`).
- **Distant (Mistral, etc.)** — `LLM_BASE_URL=https://api.mistral.ai`, `LLM_API_KEY` obligatoire, modèle distant (ex. `mistral-small-latest`).

### Review mensuelle

Ces trois variables contrôlent les seuils et la quantité de données envoyées au LLM lors de la review de fin de mois.

| Variable | Défaut | Rôle |
| --- | --- | --- |
| `REVIEW_MIN_MESSAGES` | `5` | Nombre minimal de messages dans le mois pour déclencher une review pour un utilisateur |
| `REVIEW_TOP_WORST_CATEGORIES` | `3` | Nombre de catégories d'évaluation les plus faibles à analyser |
| `REVIEW_WORST_MESSAGES_PER_CATEGORY` | `5` | Nombre de messages les plus mauvais par catégorie envoyés au LLM pour générer le feedback |

---

## 8. Tests

Les tests sont dans `tests/` et se divisent en deux familles, chacune marquée avec un `pytest.mark`.

### 8.1. Tests unitaires (`@pytest.mark.unit`)

Dossier : `tests/unit/`

Testent la logique pure sans I/O : calculs de score, pondération des critères, préparation des données pour le LLM, parsing des réponses. Ils tournent sans Docker, sans base de données, sans réseau.

```txt
tests/unit/llm/
├── test_scoring.py       # compute_weighted_score, compute_likes_score, build_scores
├── test_preparation.py   # construction du payload LLM depuis les données DB
├── test_service.py       # orchestration de l'évaluation (mocks LLM)
├── test_worker.py        # worker Taskiq (mocks)
├── test_ollama_connector.py
├── test_benchmark.py
└── test_datasets.py
```

### 8.2. Tests d'intégration (`@pytest.mark.integration`)

Dossier : `tests/integration/`

Testent le stack complet : requête HTTP → service → repository → base de données réelle. Requièrent PostgreSQL (lancé via Docker Compose).

**Infrastructure de test (conftest.py) :**

- Au démarrage de la session, un fixture `_bootstrap_test_db` crée automatiquement la base `{DB_NAME}_test`, applique toutes les migrations Alembic, et la détruit en fin de session.
- Chaque test reçoit une `db_session` qui fait un `ROLLBACK` à la fin — isolation garantie sans recréer la base entre chaque test.
- L'authentification (`verify_api_key`) et le scheduler APScheduler sont surchargés par des stubs — pas besoin de vraie clé ni de cron pendant les tests.

```txt
tests/integration/
├── messages/test_create.py          # POST /messages/ — création, déduplication, évaluation créée
├── evaluations/test_get.py          # GET /evaluations/{id}
├── totems/test_list.py              # GET /totems/
├── users/
│   ├── test_totems_by_month.py
│   ├── test_totems_history.py
│   ├── test_feedback_by_month.py
│   └── test_feedbacks_history.py
└── review/test_monthly_review.py    # pipeline complète : éligibilité, feedback, totems
```

### 8.3. Tests IA (`@pytest.mark.ai`)

Sous-ensemble des tests d'intégration qui déclenchent un vrai appel LLM. Ils sont séparés pour pouvoir être exclus en CI ou en développement rapide.

Avec `LLM_USE_MOCK=true` dans `.env`, les connecteurs LLM renvoient des stubs aléatoires — aucun appel réseau réel. C'est la configuration recommandée pour la CI.

### 8.4. Commandes

```bash
# Lancer tous les tests
make test

# Avec rapport de couverture
make test-cov

# Uniquement les tests unitaires (rapide, sans Docker)
pytest -m unit

# Exclure les tests qui appellent le LLM
pytest -m "not ai"
```

---

## 9. Mise en production

### 9.1. Architecture de la stack prod

```txt
Internet
    │  HTTPS (443) / HTTP (80)
    ▼
┌─────────────────────────────────────┐
│  proxy (Caddy)  — TLS + gzip        │
└──────────────┬──────────────────────┘
               │  HTTP interne
               ▼
┌─────────────────────────────────────┐  ┌──────────────────────────────┐
│  api (FastAPI)   APP_WORKERS=N      │  │  worker (Taskiq)             │
└──────────────┬──────────────────────┘  └──────────────┬───────────────┘
               │                                         │
               └──────────────┬──────────────────────────┘
                              │
               ┌──────────────┴───────────┐
               │                          │
               ▼                          ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│  redis                   │  │  postgres                 │
│  broker + rate limiting  │  │  données sur volume Docker│
└──────────────────────────┘  └──────────────────────────┘
```

---

### 9.2. Prérequis

- Un VPS avec Docker et Docker Compose v2 installés.
- Un domaine pointant vers l'IP du VPS (pour les certificats TLS automatiques via Caddy).
- Une base de données PostgreSQL managée (RDS, Cloud SQL, Supabase, Neon…) accessible depuis le VPS.
- Un repository GitHub (le registry `ghcr.io` est inclus gratuitement).

---

### 9.3. Configuration — GitHub Secrets & Variables

**Principe :** le CI génère le `.env` prod à chaque déploiement à partir des valeurs stockées dans GitHub. Le fichier `.env` sur le VPS est toujours synchronisé avec ce que GitHub sait — il n'est jamais édité à la main.

```txt
GitHub Secrets / Variables
        │
        ▼  (à chaque deploy)
   CI génère .env
        │
        ▼  (scp)
  /opt/nyaya/.env  ←  seule copie des valeurs prod, toujours fraîche
```

Aller dans **Settings → Secrets and variables → Actions** pour configurer :

#### Secrets (valeurs sensibles — chiffrées, masquées dans les logs)

| Nom              | Générer                | Description                                                                       |
| ---------------- | ---------------------- | --------------------------------------------------------------------------------- |
| `VPS_HOST`       | —                      | IP ou hostname du VPS                                                             |
| `VPS_USER`       | `nyaya`                | Utilisateur SSH dédié à l'app (voir §9.4)                                         |
| `VPS_SSH_KEY`    | voir §9.4              | Clé privée complète de la paire générée pour le CI                                |
| `DB_PASSWORD`    | `openssl rand -hex 32` | Mot de passe PostgreSQL                                                           |
| `REDIS_PASSWORD` | `openssl rand -hex 32` | Mot de passe Redis                                                                |
| `API_KEY`        | `openssl rand -hex 64` | Clé partagée pour le header `X-API-Key`                                           |
| `JWT_SECRET_KEY` | `openssl rand -hex 64` | Clé de signature des tokens JWT                                                   |
| `LLM_API_KEY`    | —                      | Clé API du provider LLM distant (Mistral, OpenAI…) — laisser vide si Ollama local |

> Pour `VPS_SSH_KEY` : ne pas réutiliser une clé personnelle — générer une paire dédiée (voir §9.4). Copier la **clé privée** dans le secret, la **clé publique** est ajoutée sur le VPS lors du setup initial.

#### Variables (config non-sensible — visibles dans les logs)

| Nom                                  | Exemple prod                  | Description                                                 |
| ------------------------------------ | ----------------------------- | ----------------------------------------------------------- |
| `CADDY_DOMAIN`                       | `api.exemple.com`             | Domaine pour le certificat TLS Let's Encrypt                |
| `APP_WORKERS`                        | `2`                           | Workers uvicorn — mettre le nombre de vCPUs du VPS          |
| `CORS_ORIGINS`                       | `["https://app.exemple.com"]` | Origines CORS autorisées                                    |
| `DB_NAME`                            | `nyaya_db`                    | Nom de la base (utilisé par le container postgres ET l'app) |
| `DB_USER`                            | `nyaya_user`                  | Utilisateur PostgreSQL (idem)                               |
| `LLM_BASE_URL`                       | `https://api.mistral.ai`      | URL de base du provider LLM                                 |
| `LLM_MODEL`                          | `mistral-small-latest`        | Modèle LLM à utiliser                                       |
| `LLM_TIMEOUT_SECONDS`                | `60`                          | Timeout max d'attente d'une réponse LLM                     |
| `REVIEW_MIN_MESSAGES`                | `5`                           | Messages min dans le mois pour déclencher une review        |
| `REVIEW_TOP_WORST_CATEGORIES`        | `3`                           | Nombre de catégories à analyser                             |
| `REVIEW_WORST_MESSAGES_PER_CATEGORY` | `5`                           | Messages les plus mauvais par catégorie envoyés au LLM      |

> `DB_HOST=postgres`, `DB_PORT=5432`, `REDIS_HOST=redis`, `REDIS_PORT=6379` et `JWT_ALGORITHM=HS256` sont hardcodés dans le workflow — ce sont des noms de services Docker internes qui ne changent jamais.

---

### 9.4. Première mise en production

Opérations à faire **une seule fois** — ensuite, tout passe par le CI.

#### Étape 1 — Générer la paire de clés SSH dédiée (sur la machine de dev)

Ne jamais réutiliser une clé personnelle pour le CI. Une clé dédiée peut être révoquée indépendamment.

```bash
ssh-keygen -t ed25519 -C "github-actions-nyaya" -f ~/.ssh/id_ed25519_nyaya_deploy -N ""
# Génère :
#   ~/.ssh/id_ed25519_nyaya_deploy      ← clé privée → GitHub Secret VPS_SSH_KEY
#   ~/.ssh/id_ed25519_nyaya_deploy.pub  ← clé publique → VPS (étape 2)
```

#### Étape 2 — Initialiser le VPS (en root ou sudo)

`/opt` appartient à `root` — il faut les droits sudo pour créer le dossier et configurer l'utilisateur. Le script `scripts/vps-init.sh` fait tout en une commande :

```bash
# Copier le script sur le VPS et l'exécuter
scp scripts/vps-init.sh root@vps:/tmp/
ssh root@vps "bash /tmp/vps-init.sh '$(cat ~/.ssh/id_ed25519_nyaya_deploy.pub)'"
```

Ce que fait le script :
- Crée l'utilisateur `nyaya` (mot de passe verrouillé — SSH key uniquement)
- Définit `/opt/nyaya` comme home directory avec les bonnes permissions (`750`)
- Ajoute `nyaya` au groupe `docker` (nécessaire pour lancer `docker compose` sans sudo)
- Configure `~/.ssh/authorized_keys` avec la clé publique fournie

Vérifier que la connexion fonctionne avant de continuer :

```bash
ssh -i ~/.ssh/id_ed25519_nyaya_deploy nyaya@vps "whoami && docker info | head -3"
# Doit afficher : nyaya, puis les infos Docker
```

#### Étape 3 — Configurer GitHub Secrets & Variables

Renseigner tous les secrets et variables listés au §9.3 :

- `VPS_USER` = `nyaya`
- `VPS_SSH_KEY` = contenu de `~/.ssh/id_ed25519_nyaya_deploy` (clé **privée**)
- Tous les autres secrets et variables de l'application

#### Étape 4 — Premier déploiement

```bash
git push origin main
# Le CI génère le .env, copie les fichiers de config, démarre la stack.
```

Caddy obtient son certificat Let's Encrypt automatiquement au premier démarrage — le domaine doit résoudre vers le VPS avant ce premier `push`.

**Ordre de démarrage garanti par les `depends_on` dans `docker-compose.prod.yml` :**

1. `redis` démarre et passe son healthcheck.
2. `migrate` s'exécute (`alembic upgrade head`) et quitte avec code 0.
3. `api` et `worker` démarrent seulement si `migrate` a réussi et `redis` est healthy.
4. `proxy` (Caddy) démarre seulement quand `api` passe son healthcheck.

---

### 9.5. Pipeline CI/CD

Fichier : `.github/workflows/deploy.yml`

```txt
push → main  (ou workflow_dispatch)
  │
  ├── test
  │     ├── Postgres + Redis en service containers
  │     ├── pytest -m "not ai"  (unit + intégration, LLM_USE_MOCK=true)
  │     └── ✅ ou ❌ — la suite est bloquée si les tests échouent
  │
  ├── build  (si test ✅)
  │     ├── docker build
  │     ├── push :latest → ghcr.io
  │     └── push :<sha-complet> → ghcr.io  (utilisé pour le déploiement et le rollback)
  │
  └── deploy  (si build ✅)
        ├── Génère .env prod depuis GitHub Secrets + Variables
        ├── scp .env + docker-compose.prod.yml + Caddyfile → VPS
        └── SSH : pull → migrate → up -d → image prune
```

Le `.env` prod est **généré à chaque déploiement** — il n'existe pas dans le repository et n'est jamais édité à la main sur le VPS. Modifier un secret ou une variable dans GitHub + re-déclencher le workflow suffit à mettre à jour la config en production.

---

### 9.6. Ajouter ou modifier une variable d'environnement

**Modifier une variable existante :**
1. GitHub → Settings → Secrets and variables → Actions
2. Modifier la valeur
3. Déclencher un déploiement manuellement (sans push) : **Actions → CI/CD → Run workflow → main**

**Ajouter une nouvelle variable :**
1. Ajouter la valeur dans GitHub Secrets ou Variables
2. Ajouter la ligne correspondante dans la section `Generate .env` du workflow (`.github/workflows/deploy.yml`)
3. Pusher — le déploiement se déclenche automatiquement

> Le `workflow_dispatch` (déclenchement manuel) est dans l'interface GitHub Actions. Il est utile pour forcer un redéploiement à secret constant, sans toucher au code.

---

### 9.7. Rollback

Chaque déploiement pousse deux tags sur `ghcr.io` : `:latest` et `:<sha-complet>`. Pour revenir à une version précédente :

```bash
# 1. Trouver le SHA cible dans git log ou l'interface GitHub
PREVIOUS_SHA=<sha-du-commit-cible>

# 2. Sur le VPS : pointer DOCKER_IMAGE vers ce SHA et redéployer
ssh user@vps "
  cd /opt/nyaya &&
  sed -i \"s|^DOCKER_IMAGE=.*|DOCKER_IMAGE=ghcr.io/<org>/<repo>:${PREVIOUS_SHA}|\" .env &&
  docker compose -f docker-compose.prod.yml pull &&
  docker compose -f docker-compose.prod.yml run --rm migrate &&
  docker compose -f docker-compose.prod.yml up -d --remove-orphans
"
```

Si le rollback implique d'annuler une migration (cas rare) :

```bash
ssh user@vps "
  cd /opt/nyaya &&
  docker compose -f docker-compose.prod.yml run --rm migrate downgrade -1
"
```

> Après un rollback, le prochain `push` sur `main` relancera le pipeline et repassera sur la dernière version. Si le rollback doit durer, créer une branche de fix ou reverter le commit problématique.

---

### 9.8. Opérations courantes

```bash
# Logs en temps réel (tous les services)
docker compose -f docker-compose.prod.yml logs -f

# Logs d'un service spécifique
docker compose -f docker-compose.prod.yml logs -f api
docker compose -f docker-compose.prod.yml logs -f worker

# État des services (uptime, ports, healthcheck)
docker compose -f docker-compose.prod.yml ps

# Redémarrer un seul service sans downtime sur les autres
docker compose -f docker-compose.prod.yml restart api

# Appliquer manuellement les migrations (si besoin hors-CI)
docker compose -f docker-compose.prod.yml run --rm migrate

# Libérer les images Docker inutilisées
docker image prune -f
```
