from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from llm.config import load_config
from llm.connectors.factory import build_llm
from llm.evaluation import (
    AsyncMessageEvaluationWorker,
    JsonlEvaluationEventSink,
    JsonlEvaluationRepository,
    MessageEvaluationInput,
    MessageEvaluationService,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Traite un lot de messages et persiste les évaluations JSONL.",
    )
    parser.add_argument("input", help="Fichier JSONL contenant une requête par ligne.")
    parser.add_argument(
        "--config",
        default=str(Path(__file__).with_name("config.toml")),
        help="Chemin vers le fichier TOML de configuration.",
    )
    parser.add_argument(
        "--evaluation-store",
        default="data/message_evaluations.jsonl",
        help="Fichier JSONL append-only des évaluations persistées.",
    )
    parser.add_argument(
        "--event-store",
        default="data/message_evaluation_events.jsonl",
        help="Fichier JSONL append-only des événements émis.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=4,
        help="Nombre maximum de workers parallèles.",
    )
    return parser.parse_args()


def load_requests(path: str | Path) -> list[MessageEvaluationInput]:
    requests: list[MessageEvaluationInput] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for index, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            requests.append(MessageEvaluationInput.model_validate(payload))
    if not requests:
        raise SystemExit("Aucune requête valide trouvée dans le fichier JSONL.")
    return requests


async def run() -> int:
    args = parse_args()
    cfg = load_config(args.config)
    client = build_llm(cfg)
    repository = JsonlEvaluationRepository(args.evaluation_store)
    event_sink = JsonlEvaluationEventSink(args.event_store)
    service = MessageEvaluationService(
        client=client,
        repository=repository,
        event_sink=event_sink,
        model_name=(
            cfg.ollama.model
            if cfg.llm.backend == "ollama"
            else cfg.mistral.model
        ),
        temperature=cfg.llm.temperature,
        max_tokens=cfg.llm.max_tokens,
    )
    worker = AsyncMessageEvaluationWorker(service, concurrency=args.concurrency)
    requests = load_requests(args.input)
    records = await worker.process_batch(requests)
    success_count = sum(1 for record in records if record.status == "success")
    failure_count = len(records) - success_count
    print(
        json.dumps(
            {
                "processed": len(records),
                "success": success_count,
                "failed": failure_count,
                "evaluation_store": str(Path(args.evaluation_store)),
                "event_store": str(Path(args.event_store)),
            },
            ensure_ascii=False,
        )
    )
    return 0 if failure_count == 0 else 1


def main() -> int:
    return asyncio.run(run())


if __name__ == "__main__":
    raise SystemExit(main())
