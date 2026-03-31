from __future__ import annotations

import json
from typing import Any


def parse_structured_output(text: str, output_type: Any) -> Any:
    if hasattr(output_type, "model_validate_json"):
        return output_type.model_validate_json(text)

    data = json.loads(text)

    if hasattr(output_type, "model_validate"):
        return output_type.model_validate(data)
    if output_type is dict:
        return data
    if isinstance(output_type, type):
        return output_type(**data)
    return data
