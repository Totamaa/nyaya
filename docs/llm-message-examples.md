# Exemples de messages pour l'évaluation LLM

Exemples de payloads compatibles avec `MessageEvaluationInput` utilisés pour tester le pipeline d'évaluation.

## Commentaire en réponse à un message parent

```json
{
  "content_id": "c_900",
  "content_type": "comment",
  "text": "Je ne suis pas d'accord avec cet argument.",
  "created_at": "2026-02-26T10:00:00Z",
  "author_id": 15,
  "parent": {
    "content_id": "c_842",
    "text": "Le nucléaire est dangereux car il produit des déchets.",
    "author_id": 9,
    "created_at": "2026-02-26T09:30:00Z"
  },
  "thread_root": {
    "content_id": "c_842",
    "text": "Le nucléaire est dangereux car il produit des déchets."
  },
  "context": {
    "edito_id": 12,
    "phase": "causes",
    "topic_id": 3,
    "tags": ["energie"]
  }
}
```

## Post initial (sans parent)

```json
{
  "content_id": "p_901",
  "content_type": "post",
  "text": "Je pense qu'on devrait commencer par mesurer les causes principales de retard avant de modifier le processus.",
  "created_at": "2026-02-26T10:15:00Z",
  "author_id": 21,
  "context": {
    "edito_id": 12,
    "phase": "causes",
    "topic_id": 3,
    "tags": ["energie", "organisation"]
  }
}
```

## Champs évalués par le LLM

| Champ | Description |
|-------|-------------|
| `content_type` | `post` ou `comment` |
| `text` | Texte du message à évaluer |
| `parent.text` | Texte du message parent (requis pour `comment`) |
| `thread_root.text` | Texte racine du fil |
| `context` | Contexte éditorial (edito, topic, phase, tags) |

## Schéma de sortie (`LLMMessageEvaluationOutput`)

9 critères notés de 1 à 5 + `analysis_summary` + `model_confidence` (0–1).
Voir [src/app/modules/llm/evaluation/models.py](../src/app/modules/llm/evaluation/models.py) pour le schéma complet.
