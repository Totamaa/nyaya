from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.app.modules.llm.config import load_config
from src.app.modules.llm.connectors.factory import build_llm


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pose une question au LLM configuré.")
    parser.add_argument("question", nargs="?", help="Question à envoyer au modèle.")
    parser.add_argument(
        "--config",
        default=str(Path(__file__).with_name("config.toml")),
        help="Chemin vers le fichier TOML de configuration.",
    )
    return parser.parse_args()


def build_messages(system_prompt: str, question: str) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    if system_prompt.strip():
        messages.append({"role": "system", "content": system_prompt.strip()})
    messages.append({"role": "user", "content": question.strip()})
    return messages


def main() -> int:
    args = parse_args()
    question = args.question.strip() if args.question else input("Question > ").strip()
    if not question:
        raise SystemExit("Aucune question fournie.")

    cfg = load_config(args.config)
    client = build_llm(cfg)
    response = client.complete_text(
        build_messages(cfg.llm.system_prompt, question),
        temperature=cfg.llm.temperature,
        max_tokens=cfg.llm.max_tokens,
    )
    print(response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
