from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SRC_DIR = Path(__file__).resolve().parents[3]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

_DEFAULT_DATASET_DIR = Path(__file__).resolve().parents[4] / "tests" / "data" / "llm"

from app.modules.llm.evaluation.datasets import (  # noqa: E402
    EndToEndControlDataset,
    FallacyControlDataset,
    RangeControlDataset,
    equalize_range_datasets,
    load_dataset,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Normalise et exporte les datasets de contrôle au format message "
            "(`input` compatible MessageEvaluationInput / ENTREE_MESSAGE)."
        ),
    )
    parser.add_argument(
        "--dataset-dir",
        default=str(_DEFAULT_DATASET_DIR),
        help="Répertoire contenant les fichiers JSON source.",
    )
    parser.add_argument(
        "--dataset",
        action="append",
        default=[],
        help="Chemin explicite vers un dataset JSON. Peut être répété.",
    )
    parser.add_argument(
        "--output",
        default="data/training_messages_equalized.jsonl",
        help="Fichier JSONL de sortie.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Seed déterministe pour l'égalisation.",
    )
    parser.add_argument(
        "--target-size",
        type=int,
        default=0,
        help=(
            "Taille cible des datasets de critères. 0 => taille minimum observée "
            "parmi les datasets de critères."
        ),
    )
    parser.add_argument(
        "--equalize-range",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Égalise les datasets de critères (`*_control`) avant export.",
    )
    parser.add_argument(
        "--include-fallacies",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Inclut le dataset de sophismes dans l'export.",
    )
    parser.add_argument(
        "--include-end-to-end",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Inclut le dataset end-to-end dans l'export.",
    )
    return parser.parse_args()


def resolve_dataset_paths(args: argparse.Namespace) -> list[Path]:
    explicit = [Path(path) for path in args.dataset]
    if explicit:
        paths = explicit
    else:
        paths = sorted(Path(args.dataset_dir).glob("*.json"))
    if not paths:
        raise SystemExit("Aucun dataset trouvé.")
    return paths


def _range_records(dataset: RangeControlDataset) -> list[dict[str, Any]]:
    criterion = dataset.criterion or dataset.dataset_name.removesuffix("_control")
    return [
        {
            "dataset_name": dataset.dataset_name,
            "item_id": item.id,
            "task_type": "criterion_range",
            "criterion": criterion,
            "input": item.to_message_input_payload(dataset_name=dataset.dataset_name),
            "expected": {
                "score_range": [item.expected_score_range[0], item.expected_score_range[1]],
            },
        }
        for item in dataset.items
    ]


def _fallacy_records(dataset: FallacyControlDataset) -> list[dict[str, Any]]:
    return [
        {
            "dataset_name": dataset.dataset_name,
            "item_id": item.id,
            "task_type": "fallacy_detection",
            "input": item.to_message_input_payload(dataset_name=dataset.dataset_name),
            "expected": item.expected.model_dump(),
        }
        for item in dataset.items
    ]


def _end_to_end_records(dataset: EndToEndControlDataset) -> list[dict[str, Any]]:
    return [
        {
            "dataset_name": dataset.dataset_name,
            "item_id": item.id,
            "task_type": "end_to_end",
            "input": dict(item.input),
            "expected": item.expected.model_dump(),
        }
        for item in dataset.items
    ]


def run() -> int:
    args = parse_args()
    dataset_paths = resolve_dataset_paths(args)

    range_datasets: list[RangeControlDataset] = []
    fallacy_datasets: list[FallacyControlDataset] = []
    end_to_end_datasets: list[EndToEndControlDataset] = []

    for dataset_path in dataset_paths:
        dataset = load_dataset(dataset_path)
        if isinstance(dataset, RangeControlDataset):
            range_datasets.append(dataset)
        elif isinstance(dataset, FallacyControlDataset):
            fallacy_datasets.append(dataset)
        else:
            end_to_end_datasets.append(dataset)

    range_items_before = sum(len(dataset.items) for dataset in range_datasets)
    if args.equalize_range and range_datasets:
        range_datasets = equalize_range_datasets(
            range_datasets,
            target_size=(args.target_size if args.target_size > 0 else None),
            seed=args.seed,
        )

    records: list[dict[str, Any]] = []
    for dataset in range_datasets:
        records.extend(_range_records(dataset))
    if args.include_fallacies:
        for dataset in fallacy_datasets:
            records.extend(_fallacy_records(dataset))
    if args.include_end_to_end:
        for dataset in end_to_end_datasets:
            records.extend(_end_to_end_records(dataset))

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    summary = {
        "input_dataset_count": len(dataset_paths),
        "range_dataset_count": len(range_datasets),
        "range_items_before": range_items_before,
        "range_items_after": sum(len(dataset.items) for dataset in range_datasets),
        "fallacy_dataset_count": len(fallacy_datasets),
        "end_to_end_dataset_count": len(end_to_end_datasets),
        "records_exported": len(records),
        "output": str(output_path),
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
