from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID


class Serializer(ABC):
    """Serializer abstraction for cache payloads."""

    @abstractmethod
    def dumps(self, value: Any) -> str:
        """Serialize value into string representation."""

    @abstractmethod
    def loads(self, value: str) -> Any:
        """Deserialize string representation into value."""


class JsonSerializer(Serializer):
    """JSON serializer implementation with typed payload support."""

    def dumps(self, value: Any) -> str:
        return json.dumps(self._encode(value), separators=(",", ":"))

    def loads(self, value: str) -> Any:
        return self._decode(json.loads(value))

    def _encode(self, value: Any) -> Any:
        if isinstance(value, UUID):
            return {"__type": "uuid", "value": str(value)}
        if isinstance(value, datetime):
            return {"__type": "datetime", "value": value.isoformat()}
        if isinstance(value, Decimal):
            return {"__type": "decimal", "value": str(value)}
        if isinstance(value, Enum):
            return {
                "__type": "enum",
                "value": value.value,
                "enum_class": value.__class__.__name__,
                "enum_module": value.__class__.__module__,
            }
        if isinstance(value, dict):
            return {key: self._encode(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._encode(item) for item in value]
        if isinstance(value, tuple):
            return {"__type": "tuple", "value": [self._encode(item) for item in value]}
        if isinstance(value, set):
            return {"__type": "set", "value": [self._encode(item) for item in value]}
        return value

    def _decode(self, value: Any) -> Any:
        if isinstance(value, list):
            return [self._decode(item) for item in value]
        if isinstance(value, dict):
            type_marker = value.get("__type")
            if type_marker is None:
                return {key: self._decode(item) for key, item in value.items()}

            raw_value = value.get("value")
            if type_marker == "uuid":
                return UUID(str(raw_value))
            if type_marker == "datetime":
                return datetime.fromisoformat(str(raw_value))
            if type_marker == "decimal":
                return Decimal(str(raw_value))
            if type_marker == "tuple":
                return tuple(self._decode(item) for item in raw_value or [])
            if type_marker == "set":
                return set(self._decode(item) for item in raw_value or [])
            if type_marker == "enum":
                # Enums may not be importable in all runtime contexts; keep raw value.
                return raw_value

            return {key: self._decode(item) for key, item in value.items()}
        return value
