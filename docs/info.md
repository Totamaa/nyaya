# Backend – Documentation de référence

> Document de base générique pour projets FastAPI.

---

## Table des matières

1. [Démarrage](#1-démarrage)
2. [Gestion des dépendances](#2-gestion-des-dépendances)
3. [Base de données](#3-base-de-données)
4. [Architecture](#4-architecture)
5. [Patterns architecturaux](#5-patterns-architecturaux)
6. [Tests](#6-tests)

---

## 1. Démarrage

### 1.1. Premier lancement

1. Créer un environnement virtuel : `python -m venv .venv`
2. Activer l'environnement : `.venv/Scripts/activate` (Windows) ou `source .venv/bin/activate` (Linux/Mac)
3. Installer pip-tools : `pip install pip-tools`
4. Compiler et installer les dépendances : `pip-compile requirements.in && pip-compile requirements-dev.in && pip install -r requirements-dev.txt`
5. Créer un fichier `.env` à la racine du projet, basé sur `src/app/core/config/settings.py`
6. Initialiser la base de données : `alembic upgrade head`

### 1.2. Lancer l'application

Depuis la racine du projet :

```bash
fastapi dev src/app/main.py
```

### 1.3. Créer un admin local

1. Renseigner les variables `LOCAL_*` dans `.env`
2. Exécuter : `python -m src.app.scripts.create_admin`

---

## 2. Gestion des dépendances

On utilise **pip-tools** (`pip install pip-tools`) pour séparer les dépendances de production et de développement.

### 2.1. Fichiers source

**`requirements.in`** — dépendances de production :

```txt
fastapi
uvicorn
sqlalchemy
alembic
pydantic
pydantic-settings
```

**`requirements-dev.in`** — dépendances de développement (hérite de la prod) :

```txt
-r requirements.in

pytest
pytest-asyncio
black
ruff
mypy
ipython
```

Le `-r requirements.in` est essentiel : il garantit que les versions de dev sont compatibles avec celles de prod. Toute dépendance commune est résolue une seule fois.

### 2.2. Compilation

```bash
# Générer les lockfiles
pip-compile requirements.in            # → requirements.txt
pip-compile requirements-dev.in        # → requirements-dev.txt

# Installer (dev = prod + outils dev)
pip install -r requirements-dev.txt
```

En CI/production, on installe uniquement `requirements.txt`.

### 2.3. Ajouter un package

1. Ajouter `package>=x.y,<x.(y+1)` dans le fichier `.in` approprié (prod ou dev)
2. Recompiler : `pip-compile requirements.in` (ou `requirements-dev.in`)
3. Installer : `pip install -r requirements-dev.txt`

### 2.4. Mettre à jour un package

```bash
# Un seul package (dans les limites des contraintes du .in)
pip-compile --upgrade-package package requirements.in

# Tous les packages
pip-compile --upgrade requirements.in
```

Penser à recompiler `requirements-dev.in` après avoir mis à jour `requirements.in`, car il en dépend.

### 2.5. Vérifier les packages obsolètes

1. `pip list --outdated`
2. Ajuster les contraintes dans le `.in` concerné
3. Recompiler et installer

---

## 3. Base de données

### 3.1. Modèles

Approche code-first. Pour modifier une table :

1. Modifier ou créer le modèle dans `src/app/modules/{feature}/domain/model.py`
2. Si nouveau modèle, l'enregistrer dans le `__init__.py` du module

### 3.2. Migrations

```bash
# Générer une migration
alembic revision --autogenerate -m "description_migration"

# Appliquer
alembic upgrade head
```

---

## 4. Architecture

### 4.1. Structure générale

```txt
project/
├── src/
│   └── app/
│       ├── main.py                    # Point d'entrée FastAPI (factory, lifespan, middlewares, handlers)
│       │
│       ├── modules/                   # Features métier (architecture modulaire)
│       │   ├── base/                  # Modèles et schémas de base partagés
│       │   │
│       │   ├── {feature}/            # Un module par domaine métier
│       │   │   ├── domain/            # Cœur métier (pur, sans dépendance framework)
│       │   │   │   ├── model.py           # Modèle SQLAlchemy (entité DB, relations)
│       │   │   │   ├── schemas.py         # Schémas Pydantic (Request/Response, validation)
│       │   │   │   └── exceptions.py      # Exceptions spécifiques au domaine
│       │   │   │
│       │   │   ├── application/       # Logique applicative (orchestration)
│       │   │   │   └── service.py         # Service métier (UoW, logging, orchestration)
│       │   │   │
│       │   │   ├── infrastructure/    # Accès aux données et services externes
│       │   │   │   └── repository.py      # Requêtes SQL, CRUD, eager loading
│       │   │   │
│       │   │   └── presentation/      # Interface HTTP
│       │   │       ├── router.py          # Routes FastAPI (endpoints, status codes)
│       │   │       └── dependencies.py    # Injection de dépendances (factories)
│       │   │
│       │   └── {relation}/           # Tables de relation many-to-many
│       │       └── table.py               # Table SQLAlchemy (pas de modèle complet)
│       │
│       ├── core/                      # Infrastructure transverse
│       │   ├── api/
│       │   │   ├── router_api.py              # Router principal (agrège les routers modules)
│       │   │   ├── v1/router_v1.py            # Router versionné
│       │   │   └── dependencies/              # Dépendances globales
│       │   │       ├── db.py                      # Session DB async
│       │   │       ├── auth.py                    # Authentification JWT
│       │   │       ├── request_context.py         # Request ID + contexte
│       │   │       └── uow.py                     # Factory Unit of Work
│       │   │
│       │   ├── config/
│       │   │   ├── settings.py        # Configuration (Pydantic Settings, env vars)
│       │   │   ├── database.py        # Engine/sessionmaker SQLAlchemy
│       │   │   └── logs.py            # Configuration logging structuré
│       │   │
│       │   ├── errors/
│       │   │   ├── exceptions/
│       │   │   │   ├── base.py            # AppException, BusinessException
│       │   │   │   └── db.py              # Exceptions DB
│       │   │   └── handlers/
│       │   │       ├── business.py        # Handler BusinessException
│       │   │       ├── db.py              # Handler SQLAlchemyError
│       │   │       └── catchall.py        # Handler générique (500)
│       │   │
│       │   ├── middleware/
│       │   │   ├── headers.py         # Headers (security, request_id, duration)
│       │   │   └── rate_limit.py      # Rate limiting
│       │   │
│       │   ├── security/
│       │   │   ├── hash_lib.py        # Hashing passwords
│       │   │   ├── jwt_lib.py         # Gestion JWT
│       │   │   └── anonymize_lib.py   # Anonymisation données sensibles
│       │   │
│       │   └── utils/
│       │       └── libs/
│       │           └── format_lib.py  # Formatage (normalize_last_name, etc.)
│       │
│       └── tasks/                     # Tâches asynchrones et planifiées
│           ├── scheduler.py
│           └── jobs/
│
├── migrations/                        # Alembic
│   ├── env.py
│   ├── versions/
│   └── script.py.mako
│
├── tests/
│   ├── conftest.py
│   ├── unit/
│   └── integration/
│
├── requirements.in                    # Dépendances prod (source)
├── requirements.txt                   # Dépendances prod (lockfile, généré)
├── requirements-dev.in                # Dépendances dev (source)
├── requirements-dev.txt               # Dépendances dev (lockfile, généré)
├── docker-compose.yaml
├── Dockerfile
└── alembic.ini
```

### 4.2. Types de modules

**Modules complets** (avec router, ex : `directors/`) — les 4 couches domain/application/infrastructure/presentation, CRUD exposé via API REST.

**Modules domain/data** (sans router, ex : `tokens/`) — utilisés par d'autres modules (ex : `auth` utilise `users` et `tokens`), pas d'exposition HTTP directe.

**Modules service-only** (ex : `auth/`) — logique applicative sans entité persistante propre, orchestrent plusieurs repositories via UoW.

**Tables de relation** (ex : `films_actors/`) — fichier `table.py` uniquement (Table SQLAlchemy many-to-many).

---

## 5. Patterns architecturaux

### 5.1. Layered Architecture (dans chaque module)

```txt
Presentation (Router) → Application (Service) → Infrastructure (Repository) → Domain (Model)
```

Chaque couche a une responsabilité claire :

- **Presentation** : endpoints HTTP, validation des query params, délégation au service
- **Application** : orchestration, logique métier, gestion des transactions via UoW, logging
- **Infrastructure** : requêtes SQL, CRUD, filtres, pagination, eager/lazy loading
- **Domain** : entité SQLAlchemy, relations, contraintes DB, schémas Pydantic, exceptions métier

### 5.2. Routing — simple et clean

Le router ne contient que les paramètres de la requête et le service. Toute la complexité (DB, logger, user, etc.) est cachée dans les dependencies.

```python
# ❌ Mauvais — trop de dépendances dans la signature
@router.post("/")
async def create(
    data: CreateUserRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    repo: UserRepository = Depends(get_user_repo),
    logger: Logger = Depends(get_logger),
):
    ...

# ✅ Bon — le router reste simple
@router.post("/", status_code=201)
async def create(
    data: CreateUserRequest,
    service: UserService = Depends(get_user_service),
):
    return await service.create(data)
```

### 5.3. Dependency Injection

La complexité est encapsulée dans les factories de dépendances. C'est ici que tout est câblé.

```python
# src/app/modules/users/presentation/dependencies.py

def get_user_service(
    uow: UnitOfWork = Depends(get_uow),
    context: RequestContext = Depends(get_request_context),
    logger: Logger = Depends(get_logger),
) -> UserService:
    return UserService(uow, context, logger)
```

Le `get_request_context` regroupe le `request_id` (UUID unique par requête) et le `current_user` authentifié, propagés dans les logs et les headers (`X-Request-ID`).

### 5.4. Unit of Work (UoW)

Le UoW centralise la gestion transactionnelle. Il remplace les appels manuels à `db.commit()` / `db.rollback()` et expose les repositories.

```python
# src/app/core/api/dependencies/uow.py

class UnitOfWork:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.users = UserRepository(db)
        self.tokens = TokenRepository(db)
        # ... ajouter les repos nécessaires

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, tb):
        if exc_type:
            await self.db.rollback()
        else:
            await self.db.commit()
```

Règle : **1 UoW = 1 opération métier**. Le service ouvre le contexte, travaille, et le UoW commit ou rollback automatiquement.

```python
# Dans le service
async def create(self, data: CreateUserRequest):
    async with self.uow:
        user = await self.uow.users.create(data.to_model())
        await self.uow.tokens.create_welcome_token(user.id)
        return UserResponse.from_model(user)
```

### 5.5. Include Pattern (relations)

Pour éviter le N+1 et contrôler les données chargées, on utilise un pattern `includes` explicite.

Le router reçoit les includes en query param, le service les interprète, le repository applique les jointures, et le schéma reste simple.

```python
# Router
@router.get("/")
async def list_users(
    includes: list[UserIncludeOptions] | None = Query(None),
    service: UserService = Depends(get_user_service),
):
    return await service.list(includes=includes)
```

```python
# Repository — applique les jointures conditionnellement
async def list(self, *, load_posts: bool = False):
    stmt = select(User)
    if load_posts:
        stmt = stmt.options(selectinload(User.posts))
    result = await self.db.execute(stmt)
    return result.scalars().all()
```

```python
# Service — transforme les includes en flags
async def list(self, includes: list[str] | None = None):
    includes = includes or []
    return await self.uow.users.list(
        load_posts="posts" in includes,
    )
```

Ne pas utiliser `inspect(model)` pour détecter les relations chargées — c'est explicite, pas magique.

### 5.6. Schémas — Validation et conversion

Les schémas Pydantic gèrent la validation et la conversion entre couches.

**Request schemas** : validation des entrées + méthode `to_model()` pour conversion vers le modèle SQLAlchemy.

**Response schemas** : méthode `from_model()` (classmethod) pour sérialisation + `ConfigDict(from_attributes=True)`.

**Update schemas** : tous les champs optionnels + `model_dump(exclude_unset=True)` pour ne modifier que ce qui est fourni.

### 5.7. Exception Handling

Les exceptions métier héritent de `BusinessException` avec un message orienté front et un tag pour le logging.

```python
# src/app/modules/users/domain/exceptions.py
class UserNotFoundException(BusinessException):
    def __init__(self):
        super().__init__(status_code=404, message="User not found", tag="USER")
```

Un handler centralisé transforme chaque `BusinessException` en réponse HTTP cohérente. Un handler catch-all gère les erreurs inattendues (500).

### 5.8. Request Tracking

Chaque requête reçoit un `request_id` unique (UUID) propagé dans les headers HTTP (`X-Request-ID`), les logs structurés, et le contexte async via middleware. Cela permet de tracer une requête de bout en bout.

---

## 6. Tests

### 6.1. Types de tests

Les tests sont organisés en deux catégories : `unit/` pour les tests de services, fonctions et schémas isolés, et `integration/` pour les tests API simulant des appels réels via un client de test avec base de données.

### 6.2. Structure des tests d'intégration

Dans `integration/`, un dossier par route API (auth, user, produit, etc.) avec un `common.py` partagé (variables, imports). Chaque route est découpée par fonction (ex : `auth/login/`, `auth/register/`) avec 4 fichiers :

- `test_valid.py` — cas nominaux sans erreur
- `test_constraints.py` — contraintes sur les entrées (types, tailles, nombre d'arguments) → erreurs 422
- `test_logic.py` — logique métier pouvant lever une erreur (entité introuvable, permissions, etc.)
- `test_auth.py` — contrôle d'accès (non-authentifié, rôles spécifiques)

### 6.3. Exécution

```bash
# Tous les tests
pytest

# Tests d'intégration uniquement
pytest tests/integration

# Un fichier ou dossier spécifique
pytest tests/integration/auth/login/test_valid.py

# Un test précis
pytest tests/integration/auth/login/test_valid.py::test_login_success
```
