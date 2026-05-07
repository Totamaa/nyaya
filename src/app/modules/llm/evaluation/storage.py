from __future__ import annotations

import json
import threading
from pathlib import Path

from pydantic import ValidationError

from .models import EvaluationEvent, PersistedEvaluationRecord


class JsonlEvaluationRepository:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._index: dict[tuple[str, str], PersistedEvaluationRecord] | None = None

    def _ensure_loaded(self) -> None:
        if self._index is not None:
            return
        self._index = {}
        if self.path.exists():
            with self.path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if line.strip():
                        record = self._decode_record(line)
                        if record is None:
                            continue
                        self._index[(record.content_id, record.evaluation_version)] = (
                            record
                        )

    def _decode_record(self, raw_line: str) -> PersistedEvaluationRecord | None:
        try:
            return PersistedEvaluationRecord.model_validate_json(raw_line)
        except ValidationError:
            try:
                payload = json.loads(raw_line)
            except json.JSONDecodeError:
                return None
            if "prepared_snapshot" not in payload and "context_snapshot" in payload:
                payload["prepared_snapshot"] = payload["context_snapshot"]
            try:
                return PersistedEvaluationRecord.model_validate(payload)
            except ValidationError:
                return None

    def get(
        self, content_id: str, evaluation_version: str
    ) -> PersistedEvaluationRecord | None:
        self._ensure_loaded()
        return self._index.get((content_id, evaluation_version))

    def append(self, record: PersistedEvaluationRecord) -> PersistedEvaluationRecord:
        self._ensure_loaded()
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
