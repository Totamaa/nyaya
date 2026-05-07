# Nyaya — Guide de démo

## Prérequis

```bash
# Démarrer l'API + le worker taskiq
make dev

# Peupler la base (15 users, ~20 messages chacun, évaluations comprises)
python scripts/seed.py
```

Récupère ta clé API depuis `.env` :

```bash
# PowerShell
$API_KEY = (Get-Content .env | Select-String "^API_KEY=").Line.Split("=",2)[1]
```

Swagger interactif : `http://localhost:8000/docs`

---

## Étape 1 — État initial en base

```sql
-- Vue d'ensemble
SELECT
  (SELECT COUNT(*) FROM users)       AS nb_users,
  (SELECT COUNT(*) FROM messages)    AS nb_messages,
  (SELECT COUNT(*) FROM evaluations) AS nb_evaluations;

-- Users avec leurs stats (score moyen + nb messages)
SELECT
  u.external_id,
  COUNT(m.id)                              AS nb_messages,
  ROUND(AVG(e.score_total)::numeric, 2)    AS score_moyen
FROM users u
JOIN messages m ON m.author_id = u.id
JOIN evaluations e ON e.message_id = m.id
GROUP BY u.external_id
ORDER BY score_moyen
LIMIT 5;
```

> Prends un `external_id` dans ce résultat → appelé `USER_EXTERNAL_ID` dans la suite.

---

## Étape 2 — POST /messages — message racine

```bash
curl -s -X POST http://localhost:8000/api/v1/messages/ \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "content_id": "demo-msg-001",
    "content_type": "post",
    "text": "Je pense que la réforme des retraites doit absolument prendre en compte les inégalités entre secteurs public et privé. Les données montrent clairement que le système actuel favorise certaines catégories.",
    "created_at": "2025-04-15T10:00:00Z",
    "author_id": 42,
    "likes": 12,
    "context": {
      "topic_id": 7,
      "phase": "deliberation",
      "tags": ["economie", "justice"]
    }
  }' | python -m json.tool
```

**Vérif SQL** (attendre 2-3 sec si `LLM_USE_MOCK=true`) :

```sql
-- Le message
SELECT id, external_id, content_type, LEFT(text, 60) AS text, likes, source_created_at
FROM messages
WHERE external_id = 'demo-msg-001';

-- Son évaluation générée par le LLM
SELECT e.score_total, e.clarte_des_idees, e.logique_coherence, e.pertinence, e.exactitude_verifiabilite
FROM evaluations e
JOIN messages m ON m.id = e.message_id
WHERE m.external_id = 'demo-msg-001';
```

---

## Étape 3 — GET /evaluations/{message_external_id}

```bash
curl -s http://localhost:8000/api/v1/evaluations/demo-msg-001 \
  -H "X-API-Key: $API_KEY" | python -m json.tool
```

---

## Étape 4 — POST /messages — réponse avec contexte parent

```bash
curl -s -X POST http://localhost:8000/api/v1/messages/ \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "content_id": "demo-msg-002",
    "content_type": "reply",
    "text": "Tout à fait, mais il faut aussi considérer la soutenabilité financière à long terme.",
    "created_at": "2025-04-15T10:05:00Z",
    "author_id": 99,
    "parent": {
      "content_id": "demo-msg-001",
      "text": "Je pense que la réforme des retraites doit absolument prendre en compte les inégalités entre secteurs public et privé.",
      "author_id": 42,
      "created_at": "2025-04-15T10:00:00Z"
    },
    "thread_root": {
      "content_id": "demo-msg-001",
      "text": "Je pense que la réforme des retraites doit absolument prendre en compte les inégalités entre secteurs public et privé."
    }
  }' | python -m json.tool
```

```bash
# Évaluation de la réponse
curl -s http://localhost:8000/api/v1/evaluations/demo-msg-002 \
  -H "X-API-Key: $API_KEY" | python -m json.tool
```

---

## Étape 5 — GET /totems — catalogue

```bash
curl -s http://localhost:8000/api/v1/totems/ \
  -H "X-API-Key: $API_KEY" | python -m json.tool
```

```sql
SELECT name, description, criteria FROM totems ORDER BY name;
```

---

## Étape 6 — Monthly review (feedback + totems)

```bash
# Déclencher la review mensuelle
python src/app/background/trigger_montlhy_review.py
```

**SQL** pour voir les résultats après exécution :

```sql
-- Feedbacks générés
SELECT
  u.external_id,
  f.month,
  LEFT(f.content, 120)   AS apercu,
  f.worst_categories
FROM feedbacks f
JOIN users u ON u.id = f.user_id
ORDER BY f.created_at DESC
LIMIT 5;

-- Totems attribués
SELECT
  u.external_id,
  t.name,
  ut.month,
  ut.criteria
FROM user_totems ut
JOIN users u ON u.id = ut.user_id
JOIN totems t ON t.id = ut.totem_id
ORDER BY ut.month DESC, u.external_id
LIMIT 10;
```

---

## Étape 7 — GET feedback & totems via API

Remplace `USER_EXTERNAL_ID` par un `external_id` récupéré à l'étape 1, et `YYYY-MM` par le mois précédent.

```bash
# Feedback d'un mois donné
curl -s "http://localhost:8000/api/v1/users/USER_EXTERNAL_ID/2025-04/feedback" \
  -H "X-API-Key: $API_KEY" | python -m json.tool

# Historique des feedbacks (6 derniers mois)
curl -s "http://localhost:8000/api/v1/users/USER_EXTERNAL_ID/feedbacks?limit=6" \
  -H "X-API-Key: $API_KEY" | python -m json.tool

# Totems d'un mois donné
curl -s "http://localhost:8000/api/v1/users/USER_EXTERNAL_ID/2025-04/totems" \
  -H "X-API-Key: $API_KEY" | python -m json.tool

# Historique des totems
curl -s "http://localhost:8000/api/v1/users/USER_EXTERNAL_ID/totems?limit=6" \
  -H "X-API-Key: $API_KEY" | python -m json.tool
```

---

## Ordre recommandé

1. `make dev` + `python scripts/seed.py`
2. SQL — état initial (étape 1)
3. POST message racine → GET évaluation (étapes 2-3)
4. POST réponse avec parent → GET évaluation (étape 4)
5. GET catalogue totems (étape 5)
6. Trigger review → SQL feedbacks/totems (étape 6)
7. GET feedback + totems via API (étape 7)
