"""The metric registry: one code path for every place, real or grown.

Two metric kinds (see base.py): `NetworkMetric` runs on each network layer and
emits `<name>_<layer>`; `PlaceMetric` runs on the whole context and emits
`<name>`. `run` never raises and never silently drops a metric -- a missing
layer or requirement becomes a logged NaN with status "missing_requires".
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Iterator

import pandas as pd

from cycleform.metrics.base import (
    REQUIREMENTS,
    MetricResult,
    Network,
    NetworkMetric,
    PlaceContext,
    PlaceMetric,
)

log = logging.getLogger(__name__)


class Registry:
    """Holds every metric. `run` never raises and never silently drops one."""

    def __init__(self) -> None:
        self._network: dict[str, NetworkMetric] = {}
        self._place: dict[str, PlaceMetric] = {}

    def register_network(self, m: NetworkMetric) -> NetworkMetric:
        self._check_name(m.name)
        self._network[m.name] = m
        return m

    def register_place(self, m: PlaceMetric) -> PlaceMetric:
        self._check_name(m.name)
        unknown = set(m.requires) - REQUIREMENTS
        if unknown:
            raise ValueError(f"{m.name}: unknown requirements {sorted(unknown)}")
        self._place[m.name] = m
        return m

    def _check_name(self, name: str) -> None:
        if name in self._network or name in self._place:
            raise ValueError(f"duplicate metric name: {name!r}")

    def __len__(self) -> int:
        return len(self._network) + len(self._place)

    def __iter__(self) -> Iterator[NetworkMetric | PlaceMetric]:
        yield from self._network.values()
        yield from self._place.values()

    @property
    def names(self) -> list[str]:
        """Base metric names (before layer suffixing)."""
        return sorted([*self._network, *self._place])

    def output_columns(self) -> list[str]:
        """Every column name run() can emit, layer suffixes included."""
        cols = [f"{m.name}_{layer}" for m in self._network.values() for layer in m.layers]
        cols += list(self._place)
        return sorted(cols)

    def run(self, ctx: PlaceContext, only: Iterable[str] | None = None) -> list[MetricResult]:
        """Run every metric over one place. Returns a result per emitted column."""
        want = set(only) if only is not None else None
        results: list[MetricResult] = []

        for m in self._network.values():
            for layer in m.layers:
                col = f"{m.name}_{layer}"
                if want is not None and col not in want and m.name not in want:
                    continue
                net = getattr(ctx, layer, None)
                if not isinstance(net, Network):
                    results.append(self._missing(ctx, col, m.version, layer))
                    continue
                results.append(self._safe(ctx, col, m.version, lambda n=net, f=m.fn: f(n)))

        for m in self._place.values():
            if want is not None and m.name not in want:
                continue
            missing = ctx.missing(m.requires)
            if missing:
                results.append(self._missing(ctx, m.name, m.version, ",".join(sorted(missing))))
                continue
            results.append(self._safe(ctx, m.name, m.version, lambda f=m.fn: f(ctx)))
        return results

    def _missing(self, ctx: PlaceContext, col: str, version: str, detail: str) -> MetricResult:
        log.info("%s: %s skipped, missing %s", ctx.place_id, col, detail)
        return MetricResult(ctx.place_id, col, version, float("nan"), "missing_requires", detail)

    def _safe(
        self, ctx: PlaceContext, col: str, version: str, call: Callable[[], float]
    ) -> MetricResult:
        try:
            return MetricResult(ctx.place_id, col, version, float(call()), "ok", "")
        except Exception as exc:  # a broken metric must not kill the batch
            log.exception("%s: %s failed", ctx.place_id, col)
            return MetricResult(
                ctx.place_id, col, version, float("nan"), "error", f"{type(exc).__name__}: {exc}"
            )


def results_to_frame(results: Iterable[MetricResult]) -> pd.DataFrame:
    """Long frame, one row per (place, metric). Keeps status so missingness stays visible."""
    return pd.DataFrame(
        [
            {
                "place_id": r.place_id,
                "metric": r.name,
                "version": r.version,
                "value": r.value,
                "status": r.status,
                "detail": r.detail,
            }
            for r in results
        ]
    )


def results_to_wide(results: Iterable[MetricResult]) -> pd.DataFrame:
    """Wide frame, one row per place, one column per metric. NaN where not computed."""
    long = results_to_frame(results)
    if long.empty:
        return pd.DataFrame()
    return long.pivot(index="place_id", columns="metric", values="value").rename_axis(columns=None)


REGISTRY = Registry()


def network_metric(
    name: str, version: str = "0.1.0", layers: tuple[str, ...] = ("road", "bike")
) -> Callable[[Callable[[Network], float]], Callable[[Network], float]]:
    """Decorator: register a function `fn(net) -> float` as a NetworkMetric."""

    def deco(fn: Callable[[Network], float]) -> Callable[[Network], float]:
        REGISTRY.register_network(NetworkMetric(name, version, fn, layers))
        return fn

    return deco


def place_metric(
    name: str, version: str = "0.1.0", requires: Iterable[str] = ()
) -> Callable[[Callable[[PlaceContext], float]], Callable[[PlaceContext], float]]:
    """Decorator: register a function `fn(ctx) -> float` as a PlaceMetric."""

    def deco(fn: Callable[[PlaceContext], float]) -> Callable[[PlaceContext], float]:
        REGISTRY.register_place(PlaceMetric(name, version, frozenset(requires), fn))
        return fn

    return deco
