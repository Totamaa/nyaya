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
python -m llm.evaluate_batch requests.jsonl
```

Chaque ligne de `requests.jsonl` doit contenir un `MessageEvaluationInput` sérialisé en JSON.

### Tests

```bash
pytest
```

### Benchmark datasets

Pour exécuter les jeux de contrôle contre le modèle configuré :

```bash
python -m llm.benchmark_datasets
```

Pour limiter l'exécution à un dataset :

```bash
python -m llm.benchmark_datasets --dataset llm/test_dataset/relevance_control.json
```
