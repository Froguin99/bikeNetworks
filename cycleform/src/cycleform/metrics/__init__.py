"""Importing this package registers every metric onto the shared REGISTRY."""

from cycleform.metrics import centrality, density, relational, structural  # noqa: F401
from cycleform.metrics.base import (
    MetricResult,
    Network,
    NetworkMetric,
    PlaceContext,
    PlaceMetric,
    SchemaError,
)
from cycleform.metrics.registry import (
    REGISTRY,
    network_metric,
    place_metric,
    results_to_frame,
    results_to_wide,
)

__all__ = [
    "REGISTRY",
    "MetricResult",
    "Network",
    "NetworkMetric",
    "PlaceContext",
    "PlaceMetric",
    "SchemaError",
    "network_metric",
    "place_metric",
    "results_to_frame",
    "results_to_wide",
]
