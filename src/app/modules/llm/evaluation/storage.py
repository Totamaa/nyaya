from __future__ import annotations

import json
import threading
from pathlib import Path

from .models import EvaluationEvent, PersistedEvaluationRecord


class JsonlEvaluationRepository:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._index: dict[tuple[str, str], PersistedEvaluationRecord] = {}
        self._load_existing()

    def _load_existing(self) -> None:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                record = PersistedEvaluationRecord.model_validate_json(line)
                key = (record.content_id, record.evaluation_version)
                self._index[key] = record

    def get(self, content_id: str, evaluation_version: str) -> PersistedEvaluationRecord | None:
        return self._index.get((content_id, evaluation_version))

    def append(self, record: PersistedEvaluationRecord) -> PersistedEvaluationRecord:
        key = (record.content_id, record.evaluation_version)
        with self._lock:
            existing = self._index.get(key)
            if existing is not None:
                return existing
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(record.model_dump_json())
                handle.write("\n")
            self._index[key] = record
        return record


class JsonlEvaluationEventSink:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def emit(self, event: EvaluationEvent) -> None:
        with self._lock:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(event.model_dump_json())
                handle.write("\n")
