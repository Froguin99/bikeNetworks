"""Project configuration. Every path and constant lives here, never inline."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_PKG_ROOT = Path(__file__).resolve().parents[2]
_PHD_ROOT = _PKG_ROOT.parents[2]


class Settings(BaseSettings):
    """Settings load from a .env file or CYCLEFORM_* environment variables."""

    model_config = SettingsConfigDict(env_prefix="CYCLEFORM_", env_file=".env", extra="ignore")

    # --- provenance -------------------------------------------------------
    snapshot_date: str = "2025-01-01"
    """Pinned OSM snapshot. Every derived artefact is keyed on this."""
    metric_version: str = "0.5.0"
    """Bump when any metric definition changes. Invalidates the cache.
    0.2.0: added gamma/alpha indices, orientation_order, bike_offroad_share,
    intersection_ratio_bike_road; strict protected/segregated bike classifier.
    0.3.0: added lts1/lts2 coverage, lcc_length_km, area-based densities
    (street/cycle/intersection per km2).
    0.4.0: LTS coverage + routing metrics now use the cyclable STREET network
    (roads + cycle infra), not the drive network; added mean_route_lts; added a
    `street` layer to PlaceContext.
    0.5.0: OD sampling for the routing metrics now scales with street length
    (comparable density across places), clamped [modal_od_min, modal_od_max]."""

    # --- sampling (expensive metrics) -------------------------------------
    centrality_seed: int = 42
    """Fixed seed so sampled centralities are deterministic (reproducibility)."""
    centrality_sample: int = 500
    """Source nodes sampled for betweenness/closeness. Graphs at or below this
    are computed exactly (no sampling)."""
    # Modal-directness / route-LTS OD sampling scales with street-network size so
    # sampling density is comparable across places, but is clamped so small places
    # still get enough pairs and large ones don't blow up run time.
    modal_od_per_km: float = 0.25
    """Seed OD nodes sampled per km of street network."""
    modal_od_min: int = 100
    """Floor on seed OD nodes (small places still get a stable median)."""
    modal_od_max: int = 400
    """Ceiling on seed OD nodes (bounds run time on large networks)."""
    max_road_edges: int = 200000
    """Skip a place whose RAW drive network (pre-neatnet) exceeds this: a guard
    against neatnet + sampled routing exhausting compute/memory, not a quality
    filter. Logged, not silent. Observed raw sizes: Berlin ~74k, Leeds ~71k,
    Derby ~77k, Bergamo ~111k, Brescia ~155k -- all now INCLUDED. Only region-
    scale FUAs stay capped (Oita ~233k, Okayama ~411k, Greater LA ~638k), plus
    geocoding blow-ups (Calais resolved to ~631k -- a mis-geocode, not the town).
    Override per run with the CYCLEFORM_MAX_ROAD_EDGES env var; no code edit or
    cache invalidation needed (this is not part of metric_version)."""
    batch_pause_seconds: float = 1.0
    """Small pause between places in a batch, easing sustained Overpass load."""

    # --- Overpass fetching (long batches hit transient timeouts/overload) -
    overpass_endpoints: tuple[str, ...] = (
        "https://overpass-api.de/api",
        "https://overpass.kumi.systems/api",
        "https://overpass.private.coffee/api",
    )
    """GLOBAL Overpass mirrors rotated (from a random start, to spread load) for
    each network fetch. A hard-down endpoint is skipped after a quick reachability
    probe; a slow/failing one is retried on the next mirror. Only global mirrors
    belong here: probing (2026-07) showed overpass.openstreetmap.fr returns 403
    (blocks this use) and overpass.osm.ch is a Switzerland-only extract (empty for
    everywhere else), so both are excluded. Override with CYCLEFORM_OVERPASS_ENDPOINTS
    (a JSON list) to add/reorder mirrors."""
    network_retries: int = 6
    """Attempts per network fetch, rotating through overpass_endpoints with
    backoff. Raise it for flakier connections (CYCLEFORM_NETWORK_RETRIES)."""
    overpass_probe_timeout: float = 5.0
    """Seconds to wait on the /status reachability probe before skipping a mirror
    (so a dead endpoint costs ~5s, not the full requests_timeout)."""

    # --- grown-network what-if (cycleform.scenarios) ----------------------
    scenario_prune_measure: str = "demand"
    """Which grown-network variant to read (demand | betweenness | ...)."""
    scenario_poi_source: str = "LTNs_tessellation"
    """POI seeding used by the growth model, part of the pickle filename."""
    scenario_name: str = "current_ltn_scenario"
    """Growth scenario folder/suffix (the on-street starting point)."""
    scenario_match_tol_m: float = 15.0
    """Buffer (m) for matching a grown corridor to an existing street edge. Covers
    OSM node placement + straight-line reconstruction of grown geometry."""
    scenario_cover_frac: float = 0.5
    """A street edge counts as 'on a grown corridor' (LTS -> 1) when at least this
    fraction of its length falls within the grown buffer."""

    # --- projections ------------------------------------------------------
    geographic_crs: str = "EPSG:4326"
    """CRS for boundaries and OSM data as fetched."""
    equal_area_crs: str = "ESRI:54009"
    """Mollweide. Cross-national area comparison only; not for lengths."""

    # --- paths ------------------------------------------------------------
    root: Path = _PKG_ROOT
    data: Path = _PKG_ROOT / "data"
    legacy_repo: Path = _PHD_ROOT / "bikeNetworksEDA" / "bikeNetworksEDA"
    """Predecessor repo. Read-only: a regression target, never an input."""
    growth_repo: Path = _PHD_ROOT / "networkGrowth" / "bikenwgrowth"
    """Chapter-5 growth model. Source of the LTS lookup and the grown networks."""
    grown_results_dir: Path = (
        _PHD_ROOT / "networkGrowth" / "unforked" / "bikenwgrowth_external" / "results"
    )
    """Chapter-5 grown-network outputs (per-place `<place>/<scenario>/...pickle`).
    Read-only: the source of the grown cycle networks merged in the what-if
    analysis (cycleform.scenarios). Never written to."""

    # --- 2026_edition layout (siblings of the cycleform package) ----------
    edition_root: Path = _PKG_ROOT.parent
    """The 2026_edition folder that holds the package, results and inputs."""

    @property
    def external(self) -> Path:
        """Drop-zone for input data (cycling rates, covariates). Read from here."""
        return self.edition_root / "external"

    @property
    def results(self) -> Path:
        """Per-place metrics and the combined analysis table land here."""
        return self.edition_root / "results"

    @property
    def results_places(self) -> Path:
        """One CSV per place, all metrics."""
        return self.results / "places"

    @property
    def results_scenarios(self) -> Path:
        """What-if grown-network runs (baseline + scenario per place). Kept apart
        from results_places so they never enter the cross-city analysis/model."""
        return self.results / "scenarios"

    @property
    def raw(self) -> Path:
        return self.data / "raw"

    @property
    def interim(self) -> Path:
        return self.data / "interim"

    @property
    def processed(self) -> Path:
        return self.data / "processed"

    @property
    def cache(self) -> Path:
        return self.data / "cache"

    def ensure_dirs(self) -> None:
        for p in (
            self.raw,
            self.interim,
            self.processed,
            self.cache,
            self.results,
            self.results_places,
            self.external,
        ):
            p.mkdir(parents=True, exist_ok=True)


settings = Settings()
