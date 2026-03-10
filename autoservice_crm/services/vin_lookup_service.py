from __future__ import annotations

import json
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any

from services.errors import ExternalServiceError, ValidationError
from services.validators import normalize_vin


@dataclass
class VinDecodeResult:
    vin: str
    make: str
    model: str
    model_year: int | None
    warning: str = ""


class VinLookupService:
    API_URL_TEMPLATE = "https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/{vin}?format=json"
    WMI_URL_TEMPLATE = "https://vpic.nhtsa.dot.gov/api/vehicles/DecodeWMI/{wmi}?format=json"
    USER_AGENT = "AutoServiceCRM/1.0 (+VIN lookup)"
    NON_FATAL_ERROR_CODES = {"1", "7", "8", "14", "400"}

    # Local WMI fallback for markets where NHTSA has sparse data.
    WMI_MAKE_FALLBACK = {
        "JMZ": "Mazda",
        "JM1": "Mazda",
        "JM3": "Mazda",
        "JHM": "Honda",
        "JHL": "Honda",
        "JTD": "Toyota",
        "JT3": "Toyota",
        "JT2": "Toyota",
        "JN1": "Nissan",
        "JN8": "Nissan",
        "KMH": "Hyundai",
        "KNA": "Kia",
        "KND": "Kia",
        "KNM": "Renault Samsung",
    }

    MANUFACTURER_TO_MAKE = {
        "MAZDA": "Mazda",
        "HONDA": "Honda",
        "TOYOTA": "Toyota",
        "NISSAN": "Nissan",
        "HYUNDAI": "Hyundai",
        "KIA": "Kia",
        "MERCEDES": "Mercedes-Benz",
        "BMW": "Bmw",
        "VOLKSWAGEN": "Volkswagen",
        "SKODA": "Skoda",
        "RENAULT": "Renault",
        "SUBARU": "Subaru",
        "MITSUBISHI": "Mitsubishi",
        "SUZUKI": "Suzuki",
        "LEXUS": "Lexus",
        "INFINITI": "Infiniti",
    }

    MERCEDES_PLATFORM_MAP = {
        "203": "C-Class",
        "204": "C-Class",
        "205": "C-Class",
        "206": "C-Class",
        "210": "E-Class",
        "211": "E-Class",
        "212": "E-Class",
        "213": "E-Class",
        "220": "S-Class",
        "221": "S-Class",
        "222": "S-Class",
        "223": "S-Class",
        "253": "GLC-Class",
        "463": "G-Class",
    }

    MAZDA_VDS_PREFIX_MAP = {
        "GH": "Mazda 6",
        "GJ": "Mazda 6",
        "GG": "Mazda 6",
        "BK": "Mazda 3",
        "BL": "Mazda 3",
        "BM": "Mazda 3",
        "BN": "Mazda 3",
        "KE": "CX-5",
        "KF": "CX-5",
    }

    def __init__(self):
        self._wmi_cache: dict[str, str] = {}

    def decode(self, vin: str) -> VinDecodeResult:
        normalized_vin = normalize_vin(vin, required=True)
        payload = self._fetch_payload(normalized_vin)
        record = self._extract_record(payload)
        return self._map_record(normalized_vin, record)

    def _fetch_payload(self, vin: str) -> Any:
        url = self.API_URL_TEMPLATE.format(vin=vin)
        text = self._http_get_text(url)

        stripped = text.strip()
        if not stripped:
            raise ExternalServiceError("Внешний сервис VIN вернул пустой ответ.")

        if stripped.startswith("{"):
            try:
                return json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ExternalServiceError("Не удалось разобрать JSON VIN сервиса.") from exc

        try:
            return ET.fromstring(stripped)
        except ET.ParseError as exc:
            raise ExternalServiceError("Не удалось разобрать ответ VIN сервиса.") from exc

    def _http_get_text(self, url: str) -> str:
        last_error: Exception | None = None
        for timeout in (8, 12, 20):
            request = urllib.request.Request(
                url=url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": self.USER_AGENT,
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    return response.read().decode("utf-8", errors="replace")
            except urllib.error.URLError as exc:
                last_error = exc
            except TimeoutError as exc:
                last_error = exc

        raise ExternalServiceError("Не удалось получить данные VIN от внешнего сервиса.") from last_error

    def _extract_record(self, payload: Any) -> dict:
        if isinstance(payload, dict):
            rows = payload.get("Results") or []
            if not rows:
                raise ExternalServiceError("VIN сервис не вернул данных.")
            return rows[0]

        root: ET.Element = payload
        namespace_prefix = ""
        if root.tag.startswith("{"):
            namespace_prefix = root.tag.split("}")[0] + "}"

        results_node = root.find(f".//{namespace_prefix}Results")
        if results_node is None:
            raise ExternalServiceError("VIN сервис вернул неподдерживаемый XML-формат.")

        result: dict[str, str] = {}
        for child in list(results_node):
            key = child.tag.split("}")[-1]
            result[key] = child.text or ""
        return result

    def _map_record(self, vin: str, record: dict) -> VinDecodeResult:
        make, make_fallback = self._resolve_make(record, vin)
        if not make:
            raise ValidationError("По этому VIN не удалось определить марку.")

        model, model_fallback = self._resolve_model(record, vin, make)
        model_year_raw = str(record.get("ModelYear") or "").strip()
        model_year = int(model_year_raw) if model_year_raw.isdigit() else None

        error_code_raw = str(record.get("ErrorCode") or "").strip()
        error_codes = {part.strip() for part in error_code_raw.split(",") if part.strip()}
        non_zero_codes = {code for code in error_codes if code != "0"}
        error_text = str(record.get("ErrorText") or "").strip()

        warning_parts: list[str] = []
        if make_fallback:
            warning_parts.append("Марка определена через fallback-логику (WMI/производитель).")
        if model_fallback:
            warning_parts.append("Модель определена через fallback-логику.")

        if not model:
            warning_parts.append(
                "Модель не найдена в базе NHTSA. Введите модель вручную или подключите специализированный VIN API."
            )

        if non_zero_codes:
            if non_zero_codes.issubset(self.NON_FATAL_ERROR_CODES):
                warning_parts.append(
                    "Ответ NHTSA частичный для этого VIN (часто так бывает у EU/JP/KR автомобилей)."
                )
                # In partial decode mode NHTSA year may be misleading.
                model_year = None
            elif error_text:
                warning_parts.append(error_text)

        warning = " ".join(warning_parts).strip()

        return VinDecodeResult(
            vin=vin,
            make=make,
            model=model,
            model_year=model_year,
            warning=warning,
        )

    def _resolve_make(self, record: dict, vin: str) -> tuple[str, bool]:
        make = str(record.get("Make") or "").strip()
        if make:
            return make.title(), False

        manufacturer = str(record.get("Manufacturer") or "").upper()
        for keyword, mapped_make in self.MANUFACTURER_TO_MAKE.items():
            if keyword in manufacturer:
                return mapped_make, True

        wmi = vin[:3]
        from_api = self._decode_wmi_make(wmi)
        if from_api:
            return from_api, True

        local = self.WMI_MAKE_FALLBACK.get(wmi)
        if local:
            return local, True

        return "", False

    def _resolve_model(self, record: dict, vin: str, make: str) -> tuple[str, bool]:
        model = str(record.get("Model") or "").strip()
        if model:
            return model, False

        make_lower = make.lower()
        if make_lower == "mercedes-benz":
            fallback = self.MERCEDES_PLATFORM_MAP.get(vin[3:6], "")
            if fallback:
                return fallback, True

        if make_lower == "mazda":
            # For many EU Mazda VINs NHTSA returns empty model.
            vds2 = vin[3:5]
            fallback = self.MAZDA_VDS_PREFIX_MAP.get(vds2, "")
            if fallback:
                return fallback, True

        return "", False

    def _decode_wmi_make(self, wmi: str) -> str:
        if wmi in self._wmi_cache:
            return self._wmi_cache[wmi]

        try:
            text = self._http_get_text(self.WMI_URL_TEMPLATE.format(wmi=wmi))
            data = json.loads(text)
            rows = data.get("Results") or []
            row = rows[0] if rows else {}
        except Exception:
            self._wmi_cache[wmi] = ""
            return ""

        make_raw = str(row.get("Make") or "").strip()
        if "," in make_raw:
            make_raw = make_raw.split(",")[0].strip()
        resolved = make_raw.title() if make_raw else ""
        self._wmi_cache[wmi] = resolved
        return resolved
