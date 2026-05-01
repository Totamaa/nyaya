# Nyaya — Documentation

## Table des matières

1. [Prérequis](#1-prérequis)
2. [Démarrage](#2-démarrage)
3. [Gestion des dépendances](#3-gestion-des-dépendances)
4. [Base de données](#4-base-de-données)
5. [Architecture](#5-architecture)
6. [Core](#6-core)
7. [Tests](#7-tests)
8. [Mise en production](#8-mise-en-production)

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

## 7. Tests

Les tests sont dans `tests/`. Pas encore écrits pour les endpoints HTTP — la structure est en place pour accueillir :

- `tests/unit/` — tests de services, fonctions, schémas isolés
- `tests/integration/` — tests API avec client de test et base de données réelle

```bash
# Lancer tous les tests
make test

# Avec couverture
make test-cov
```

---

## 8. Mise en production

À venir.
