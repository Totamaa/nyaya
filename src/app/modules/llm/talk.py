from __future__ import annotations

import argparse
import sys
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[3]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from app.core.config.settings import get_settings
from app.modules.llm.connectors.factory import build_llm_client


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pose une question au LLM configuré.")
    parser.add_argument("question", nargs="?", help="Question à envoyer au modèle.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    question = args.question.strip() if args.question else input("Question > ").strip()
    if not question:
        raise SystemExit("Aucune question fournie.")

    settings = get_settings()
    client = build_llm_client(
        base_url=settings.LLM_BASE_URL,
        model=settings.LLM_MODEL,
        api_key=settings.LLM_API_KEY,
        timeout_s=float(settings.LLM_TIMEOUT_SECONDS),
        use_mock=settings.LLM_USE_MOCK,
    )
    print(client.complete_text([{"role": "user", "content": question}]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
