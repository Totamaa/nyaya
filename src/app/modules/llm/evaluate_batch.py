from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[3]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from app.core.config.settings import get_settings
from app.modules.llm.connectors.factory import build_llm_client
from app.modules.llm.evaluation import (
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
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            requests.append(MessageEvaluationInput.model_validate(json.loads(stripped)))
    if not requests:
        raise SystemExit("Aucune requête valide trouvée dans le fichier JSONL.")
    return requests


async def run() -> int:
    args = parse_args()
    settings = get_settings()
    client = build_llm_client(
        base_url=settings.LLM_BASE_URL,
        model=settings.LLM_MODEL,
        api_key=settings.LLM_API_KEY,
        timeout_s=float(settings.LLM_TIMEOUT_SECONDS),
        use_mock=settings.LLM_USE_MOCK,
    )
    repository = JsonlEvaluationRepository(args.evaluation_store)
    event_sink = JsonlEvaluationEventSink(args.event_store)
    service = MessageEvaluationService(
        client=client,
        repository=repository,
        event_sink=event_sink,
        model_name=settings.LLM_MODEL,
    )
    worker = AsyncMessageEvaluationWorker(service, concurrency=args.concurrency)
    records = await worker.process_batch(load_requests(args.input))
    success_count = sum(1 for r in records if r.status == "success")
    print(
        json.dumps(
            {
                "processed": len(records),
                "success": success_count,
                "failed": len(records) - success_count,
                "evaluation_store": str(Path(args.evaluation_store)),
                "event_store": str(Path(args.event_store)),
            },
            ensure_ascii=False,
        )
    )
    return 0 if success_count == len(records) else 1


def main() -> int:
    return asyncio.run(run())


if __name__ == "__main__":
    raise SystemExit(main())
