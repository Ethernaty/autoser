from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from services.errors import ValidationError


def require_non_empty(value: str, field_name: str, max_len: int = 255) -> str:
    clean = (value or "").strip()
    if not clean:
        raise ValidationError(f"Поле «{field_name}» обязательно.")
    if len(clean) > max_len:
        raise ValidationError(f"Поле «{field_name}» слишком длинное (макс. {max_len}).")
    return clean


def normalize_optional_text(value: str, max_len: int = 2000) -> str:
    clean = (value or "").strip()
    if len(clean) > max_len:
        raise ValidationError(f"Текст слишком длинный (макс. {max_len}).")
    return clean


def normalize_phone(value: str) -> str:
    clean = require_non_empty(value, "Телефон", max_len=30)
    digits = re.sub(r"\D+", "", clean)
    if len(digits) < 6:
        raise ValidationError("Телефон указан некорректно.")
    return clean


def validate_commission_pct(value: int) -> int:
    if not isinstance(value, int):
        raise ValidationError("Процент сотрудника должен быть целым числом.")
    if value < 0 or value > 100:
        raise ValidationError("Процент сотрудника должен быть в диапазоне 0-100.")
    return value


def validate_year(value: Optional[int]) -> Optional[int]:
    if value in (None, 0):
        return None
    current_year = datetime.now().year
    if value < 1950 or value > current_year + 1:
        raise ValidationError(f"Год должен быть в диапазоне 1950-{current_year + 1}.")
    return value


def validate_money(value: float, field_name: str = "Сумма", allow_zero: bool = False) -> float:
    if value is None:
        raise ValidationError(f"Поле «{field_name}» обязательно.")
    amount = float(value)
    if amount < 0:
        raise ValidationError(f"Поле «{field_name}» не может быть отрицательным.")
    if not allow_zero and amount <= 0:
        raise ValidationError(f"Поле «{field_name}» должно быть больше нуля.")
    return round(amount, 2)


def validate_id(value: int, field_name: str) -> int:
    if not isinstance(value, int) or value <= 0:
        raise ValidationError(f"Поле «{field_name}» заполнено некорректно.")
    return value


def normalize_vin(value: str, required: bool = False) -> str:
    clean = (value or "").strip().upper()
    if not clean:
        if required:
            raise ValidationError("VIN обязателен.")
        return ""
    if len(clean) != 17:
        raise ValidationError("VIN должен содержать 17 символов.")
    if not re.fullmatch(r"[A-HJ-NPR-Z0-9]{17}", clean):
        raise ValidationError("VIN содержит недопустимые символы.")
    return clean
