from __future__ import annotations

from importlib import import_module
from typing import Any


__all__ = [
    "ChaosInjectedError",
    "ChaosPolicy",
    "get_chaos_engine",
    "FailoverManager",
    "get_failover_manager",
    "AutoScalingSignalExporter",
    "get_scaling_signal_exporter",
    "SaturationSignal",
    "SaturationReport",
    "SaturationDetector",
    "get_saturation_detector",
    "SLOMonitor",
    "get_slo_monitor",
]

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "ChaosInjectedError": ("app.core.reliability.chaos", "ChaosInjectedError"),
    "ChaosPolicy": ("app.core.reliability.chaos", "ChaosPolicy"),
    "get_chaos_engine": ("app.core.reliability.chaos", "get_chaos_engine"),
    "FailoverManager": ("app.core.reliability.failover", "FailoverManager"),
    "get_failover_manager": ("app.core.reliability.failover", "get_failover_manager"),
    "AutoScalingSignalExporter": ("app.core.reliability.scaling", "AutoScalingSignalExporter"),
    "get_scaling_signal_exporter": ("app.core.reliability.scaling", "get_scaling_signal_exporter"),
    "SaturationSignal": ("app.core.reliability.saturation", "SaturationSignal"),
    "SaturationReport": ("app.core.reliability.saturation", "SaturationReport"),
    "SaturationDetector": ("app.core.reliability.saturation", "SaturationDetector"),
    "get_saturation_detector": ("app.core.reliability.saturation", "get_saturation_detector"),
    "SLOMonitor": ("app.core.reliability.slo", "SLOMonitor"),
    "get_slo_monitor": ("app.core.reliability.slo", "get_slo_monitor"),
}


def __getattr__(name: str) -> Any:
    try:
        module_name, attr_name = _LAZY_EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
