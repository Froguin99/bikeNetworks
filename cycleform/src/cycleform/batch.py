"""Run the metric suite over many places, saving each to results/places/.

Fetching is sequential to stay friendly to the Overpass API (osmnx caches, so
re-runs are fast); metric computation is per-place. A place that fails is logged
and recorded, never silently dropped (CLAUDE.md §10) -- the batch returns a
status frame so missingness is a countable outcome.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import pandas as pd

from cycleform.config import settings
from cycleform.ingest import context_from_osm
from cycleform.metrics import REGISTRY
from cycleform.results import build_combined, is_cached, save_place

log = logging.getLogger(__name__)


@dataclass
class PlaceSpec:
    query: str
    place_id: str
    country: str = ""


def run_place(spec: PlaceSpec, *, simplify: bool = True, force: bool = False) -> dict:
    """Ingest one place, run every metric, save it. Returns a status row.

    If the place is already computed under the current metric_version and
    `force` is False, it is skipped (status "cached") -- so a long run resumes
    where it left off and re-runs never recompute unchanged places (§7).
    """
    if not force and is_cached(spec.place_id):
        return {
            "place_id": spec.place_id,
            "country": spec.country,
            "status": "cached",
            "road_edges": 0,
            "bike_edges": 0,
            "metrics_ok": 0,
            "metrics_error": 0,
            "seconds": 0.0,
            "detail": f"cached at metric_version {settings.metric_version}",
        }
    t0 = time.perf_counter()
    try:
        ctx = context_from_osm(
            spec.query, place_id=spec.place_id, country=spec.country, simplify=simplify
        )
        results = REGISTRY.run(ctx)
        save_place(ctx, results)
        n_ok = sum(1 for r in results if r.status == "ok")
        n_bad = sum(1 for r in results if r.status == "error")
        return {
            "place_id": spec.place_id,
            "country": spec.country,
            "status": "ok",
            "road_edges": ctx.road.n_edges,
            "bike_edges": ctx.bike.n_edges,
            "metrics_ok": n_ok,
            "metrics_error": n_bad,
            "seconds": round(time.perf_counter() - t0, 1),
            "detail": "",
        }
    except Exception as exc:
        log.exception("%s failed", spec.place_id)
        return {
            "place_id": spec.place_id,
            "country": spec.country,
            "status": "failed",
            "road_edges": 0,
            "bike_edges": 0,
            "metrics_ok": 0,
            "metrics_error": 0,
            "seconds": round(time.perf_counter() - t0, 1),
            "detail": f"{type(exc).__name__}: {exc}",
        }


def run_places(
    specs: list[PlaceSpec], *, simplify: bool = True, combine: bool = True, force: bool = False
) -> pd.DataFrame:
    """Run a batch. Returns a per-place status frame; builds the combined table.

    Cached places (current metric_version) are skipped unless `force`; this makes
    the run resumable after an interruption.
    """
    rows = []
    for i, spec in enumerate(specs, 1):
        log.info("[%d/%d] %s", i, len(specs), spec.place_id)
        row = run_place(spec, simplify=simplify, force=force)
        rows.append(row)
        if row["status"] == "ok" and settings.batch_pause_seconds:
            time.sleep(settings.batch_pause_seconds)  # ease sustained Overpass load
    status = pd.DataFrame(rows)
    log.info("batch done: %s", status["status"].value_counts().to_dict())
    if combine:
        build_combined()
    return status


PILOT: list[PlaceSpec] = [
    PlaceSpec("Cambridge, United Kingdom", "Cambridge, United Kingdom", "UK"),
    PlaceSpec("York, United Kingdom", "York, United Kingdom", "UK"),
    PlaceSpec("Newcastle upon Tyne, United Kingdom", "Newcastle upon Tyne, United Kingdom", "UK"),
    PlaceSpec("Oxford, United Kingdom", "Oxford, United Kingdom", "UK"),
    PlaceSpec("Groningen, Netherlands", "Groningen, Netherlands", "NL"),
    PlaceSpec("Delft, Netherlands", "Delft, Netherlands", "NL"),
    PlaceSpec("Münster, Germany", "Münster, Germany", "DE"),
    PlaceSpec("Freiburg im Breisgau, Germany", "Freiburg im Breisgau, Germany", "DE"),
    PlaceSpec("Odense Kommune, Denmark", "Odense, Denmark", "DK"),
    PlaceSpec("Davis, California, USA", "Davis, California, USA", "US"),
]


# OECD 2-letter REF_AREA prefixes -> country name for Nominatim geocoding.
COUNTRY_NAMES: dict[str, str] = {
    "UK": "United Kingdom",
    "DE": "Germany",
    "FR": "France",
    "IT": "Italy",
    "BE": "Belgium",
    "CH": "Switzerland",
    "SE": "Sweden",
    "NO": "Norway",
    "FI": "Finland",
    "PT": "Portugal",
    "IE": "Ireland",
    "US": "United States",
    "CA": "Canada",
    "AU": "Australia",
    "JP": "Japan",
    "CZ": "Czechia",
    "EE": "Estonia",
    "LV": "Latvia",
    "SK": "Slovakia",
    "BG": "Bulgaria",
    "CL": "Chile",
    "NZ": "New Zealand",
    "KO": "South Korea",
    "ME": "Mexico",
}


def all_outcome_specs() -> list[PlaceSpec]:
    """One PlaceSpec per place we have a cycling rate for (OECD FUAs + legacy).

    OECD places geocode as "Name, Country" with the country from the FUA code;
    legacy-only places (not in OECD) fall back to a bare-name query with no
    country. Deduplicated on (place_key, country). Names that Nominatim can't
    resolve to a polygon will fail at run time and be logged, never silently lost.
    """
    from cycleform.outcomes import build_outcomes

    out = build_outcomes(save=False)
    specs: dict[tuple, PlaceSpec] = {}
    # OECD first (country known), so it wins over a legacy duplicate.
    for src in ("oecd_fua", "legacy_max_value"):
        for _, r in out[out["source"] == src].iterrows():
            key = (r["place_key"], r.get("country") or "")
            if key in specs or not str(r["place_id"]).strip():
                continue
            cc = str(r["country"]) if pd.notna(r.get("country")) else ""
            if cc and cc in COUNTRY_NAMES:
                label = f"{r['place_id']}, {COUNTRY_NAMES[cc]}"
                specs[key] = PlaceSpec(label, label, cc)
            else:
                specs[key] = PlaceSpec(str(r["place_id"]), str(r["place_id"]), cc)
    # dedupe again on place_key alone, preferring the entry that carries a country
    by_place: dict[str, PlaceSpec] = {}
    for (pk, cc), spec in specs.items():
        if pk not in by_place or (cc and not by_place[pk].country):
            by_place[pk] = spec
    # Priority order: UK first (thesis focus), then core Europe, then the rest --
    # so a partial run yields the most relevant places first.
    return sorted(by_place.values(), key=lambda s: (_priority(s.country), s.place_id))


# Country priority for the run order (lower = computed first).
_CORE_EUROPE = {"DE", "FR", "IT", "NL", "BE", "CH", "SE", "NO", "FI", "PT", "IE", "DK", "ES", "AT"}


def _priority(cc: str) -> int:
    if cc == "UK":
        return 0
    if cc in _CORE_EUROPE:
        return 1
    if cc in ("US", "CA", "AU", "NZ"):
        return 2
    return 3


def _uk(name: str) -> PlaceSpec:
    return PlaceSpec(f"{name}, United Kingdom", f"{name}, United Kingdom", "UK")


def _spec(name: str, country_query: str, cc: str) -> PlaceSpec:
    return PlaceSpec(f"{name}, {country_query}", f"{name}, {country_query}", cc)


# ~50-city scale test. UK-heavy (thesis focus); the rest span countries present in
# the OECD FUA outcome extract so they can match a cycling rate. Biased toward
# small/medium cities to stay within compute limits.
SCALE_TEST: list[PlaceSpec] = [
    *[
        _uk(n)
        for n in [
            "Newcastle upon Tyne",
            "Cambridge",
            "York",
            "Oxford",
            "Bristol",
            "Sheffield",
            "Nottingham",
            "Leicester",
            "Coventry",
            "Norwich",
            "Portsmouth",
            "Southampton",
            "Brighton and Hove",
            "Reading",
            "Cardiff",
            "Derby",
            "Plymouth",
            "Exeter",
            "Lincoln",
            "Bath",
            "Ipswich",
            "Colchester",
            "Gloucester",
            "Cheltenham",
        ]
    ],
    *[
        _spec(n, "Germany", "DE")
        for n in [
            "Münster",
            "Freiburg im Breisgau",
            "Bremen",
            "Hannover",
            "Karlsruhe",
            "Bonn",
            "Heidelberg",
            "Darmstadt",
        ]
    ],
    *[
        _spec(n, "France", "FR")
        for n in [
            "Strasbourg",
            "Nantes",
            "Grenoble",
            "Rennes",
            "Dijon",
            "Angers",
        ]
    ],
    *[_spec(n, "Italy", "IT") for n in ["Bologna", "Florence", "Parma"]],
    _spec("Malmö", "Sweden", "SE"),
    _spec("Gothenburg", "Sweden", "SE"),
    _spec("Oslo", "Norway", "NO"),
    _spec("Ghent", "Belgium", "BE"),
    _spec("Bern", "Switzerland", "CH"),
    _spec("Dublin", "Ireland", "IE"),
    _spec("Porto", "Portugal", "PT"),
    _spec("Davis", "California, USA", "US"),
]
