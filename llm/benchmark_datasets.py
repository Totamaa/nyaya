from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from llm.config import load_config
from llm.connectors.factory import build_llm
from llm.evaluation.benchmark import BenchmarkRunner


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Lance un benchmark sur les datasets de contrôle Nyaya.",
    )
    parser.add_argument(
        "--dataset-dir",
        default="llm/test_dataset",
        help="Répertoire contenant les datasets JSON.",
    )
    parser.add_argument(
        "--dataset",
        action="append",
        default=[],
        help="Chemin explicite vers un dataset JSON. Peut être répété.",
    )
    parser.add_argument(
        "--config",
        default=str(Path(__file__).with_name("config.toml")),
        help="Chemin vers le fichier TOML de configuration.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Fichier JSON de sortie optionnel pour le rapport complet.",
    )
    parser.add_argument(
        "--max-datasets",
        type=int,
        default=0,
        help="Limite optionnelle sur le nombre de datasets à exécuter, 0 = pas de limite.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=0,
        help="Surcharge locale du budget max_tokens, 0 = config.",
    )
    return parser.parse_args()


def resolve_dataset_paths(args: argparse.Namespace) -> list[Path]:
    explicit = [Path(path) for path in args.dataset]
    if explicit:
        paths = explicit
    else:
        dataset_dir = Path(args.dataset_dir)
        paths = sorted(dataset_dir.glob("*.json"))
    if args.max_datasets > 0:
        paths = paths[: args.max_datasets]
    if not paths:
        raise SystemExit("Aucun dataset trouvé.")
    return paths


def print_human_summary(report: dict[str, object]) -> None:
    print(
        f"Model: {report['backend_model']} | "
        f"Datasets: {report['dataset_count']} | "
        f"Items: {report['passed_items']}/{report['total_items']} passed | "
        f"Accuracy: {report['overall_accuracy']:.2%}"
    )
    for summary in report["summaries"]:
        print(
            f"- {summary['dataset_name']}: "
            f"{summary['passed']}/{summary['total']} passed "
            f"({summary['accuracy']:.2%})"
        )
        failures = [item for item in summary["results"] if item["status"] == "failed"][:3]
        for failure in failures:
            print(
                f"  - {failure['item_id']}: expected={failure['expected']} "
                f"actual={failure.get('actual')} error={failure.get('error')}"
            )


def main() -> int:
    args = parse_args()
    dataset_paths = resolve_dataset_paths(args)
    cfg = load_config(args.config)
    client = build_llm(cfg)
    model_name = cfg.ollama.model if cfg.llm.backend == "ollama" else cfg.mistral.model
    runner = BenchmarkRunner(
        client=client,
        model_name=model_name,
        system_prompt=cfg.llm.system_prompt,
        temperature=cfg.llm.temperature,
        max_tokens=(args.max_tokens if args.max_tokens > 0 else cfg.llm.max_tokens),
    )
    report = runner.run_paths(dataset_paths)
    report_dict = report.model_dump()
    print_human_summary(report_dict)
    if args.output:
        Path(args.output).write_text(
            json.dumps(report_dict, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return 0 if report.failed_items == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
