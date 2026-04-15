# Nyaya

## Message Evaluation v1

Le dépôt contient maintenant une brique `llm.evaluation` qui :
- évalue un message via un appel LLM structuré sur 9 critères textuels,
- calcule le critère `likes` hors LLM à partir de `likes_normalized`,
- calcule le score global pondéré,
- persiste les résultats et événements en JSONL append-only,
- traite des lots via un worker asynchrone.

### Lancer un lot

```bash
PYTHONPATH=src/app/modules python -m llm.evaluate_batch requests.jsonl
```

Chaque ligne de `requests.jsonl` doit contenir un `MessageEvaluationInput` sérialisé en JSON.

### Tests

```bash
pytest
```

### Benchmark datasets

Les jeux de `src/app/modules/llm/test_dataset/*.json` utilisent un `input` au format
`MessageEvaluationInput` (même forme que les messages entrants), avec 20 items par dataset.

Pour exécuter les jeux de contrôle contre le modèle configuré :

```bash
PYTHONPATH=src/app/modules python -m llm.benchmark_datasets
```

Pour limiter l'exécution à un dataset :

```bash
PYTHONPATH=src/app/modules python -m llm.benchmark_datasets --dataset src/app/modules/llm/test_dataset/relevance_control.json
```

### Export train/test au format `ENTREE_MESSAGE`

Pour normaliser les jeux de contrôle vers un format homogène (`input` compatible `MessageEvaluationInput`)
et égaliser les datasets de critères :

```bash
PYTHONPATH=src/app/modules python -m llm.export_training_dataset --output data/training_messages_equalized.jsonl
```
