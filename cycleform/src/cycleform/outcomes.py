"""Harmonise cycling-rate outcomes into one long table (Phase 2).

One row per (place, year, source). Constructs are never silently stacked:
`source` and `measure_type` are carried through as columns so they can enter the
model as fixed effects (CLAUDE.md §4). Sources live in external/cycling_rates/.

Schema (CLAUDE.md §4):
    place_id | place_key | geom_source | year | value | numerator |
    denominator | measure_type | source | sample_n | notes
"""

from __future__ import annotations

import logging
import unicodedata

import pandas as pd

from cycleform.config import settings

log = logging.getLogger(__name__)

COLUMNS = [
    "place_id",
    "place_key",
    "country",
    "geom_source",
    "year",
    "value",
    "numerator",
    "denominator",
    "measure_type",
    "source",
    "sample_n",
    "notes",
]


def place_key(name: str) -> str:
    """Normalise a place name for joining: lowercase, de-accented, de-suffixed.

    Drops a trailing country clause ("Newcastle, United Kingdom" -> "newcastle")
    and strips diacritics ("Munchen"). Deliberately simple -- the actual join to
    metric place_ids happens in assemble.py where mismatches are logged, not here.
    """
    s = str(name).split(",")[0].strip().lower()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return " ".join(s.split())


def _read_csv_resilient(path, **kw) -> pd.DataFrame:
    """Read a CSV, retrying with cp1252 for legacy Windows-encoded files."""
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return pd.read_csv(path, encoding=enc, **kw)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path, encoding="latin-1", encoding_errors="replace", **kw)


def load_max_value() -> pd.DataFrame:
    """Legacy `max_value.csv` (Eurostat + 2011 census, mixed construct)."""
    path = settings.external / "cycling_rates" / "max_value.csv"
    raw = _read_csv_resilient(path)
    out = pd.DataFrame(
        {
            "place_id": raw["Place"],
            "place_key": raw["Place"].map(place_key),
            "country": pd.NA,  # legacy file carries no country; matched on name alone
            "geom_source": "legacy",
            "year": pd.NA,
            "value": pd.to_numeric(raw["max_value"], errors="coerce"),
            "numerator": pd.NA,
            "denominator": pd.NA,
            "measure_type": "commute_mode_share",
            "source": "legacy_max_value",
            "sample_n": pd.NA,
            "notes": "mixed Eurostat + 2011 census; year unknown",
        }
    )
    return out[COLUMNS]


def load_oecd_fua(latest_only: bool = True) -> pd.DataFrame:
    """OECD Functional Urban Area bicycle commute mode share.

    When `latest_only`, keep the most recent year per FUA (user decision).
    """
    path = settings.external / "cycling_rates" / "oecd_fua_commute_bicycle.csv"
    raw = _read_csv_resilient(path)
    b = raw[(raw["Mode of transport"] == "Bicycle") & raw["OBS_VALUE"].notna()].copy()
    b["year"] = pd.to_numeric(b["TIME_PERIOD"], errors="coerce")
    if latest_only:
        b = b.loc[b.groupby("REF_AREA")["year"].idxmax()]
    out = pd.DataFrame(
        {
            "place_id": b["Reference area"],
            "place_key": b["Reference area"].map(place_key),
            "country": b["REF_AREA"].astype(str).str[:2].str.upper(),
            "geom_source": "oecd_fua",
            "year": b["year"].astype("Int64"),
            "value": pd.to_numeric(b["OBS_VALUE"], errors="coerce"),
            "numerator": pd.NA,
            "denominator": "employed persons commuting to work",
            "measure_type": "commute_mode_share",
            "source": "oecd_fua",
            "sample_n": pd.NA,
            "notes": "FUA code " + b["REF_AREA"].astype(str),
        }
    )
    return out[COLUMNS]


def build_outcomes(save: bool = True) -> pd.DataFrame:
    """Concatenate all available sources into the harmonised long table.

    Logs per-source and total coverage (the Phase-2 gate: know N and coverage).
    Never drops a row silently -- a place present in several sources appears
    once per source, distinguished by the `source` column.
    """
    dtypes = {"year": "Int64", "value": "float64", "numerator": "Float64", "sample_n": "Float64"}
    parts = []
    for name, loader in (("legacy_max_value", load_max_value), ("oecd_fua", load_oecd_fua)):
        try:
            df = loader().astype(dtypes)
            log.info("%s: %d rows, %d unique places", name, len(df), df["place_key"].nunique())
            parts.append(df)
        except FileNotFoundError:
            log.warning("%s: source file missing, skipped", name)
    if not parts:
        return pd.DataFrame(columns=COLUMNS)
    long = pd.concat(parts, ignore_index=True)
    log.info(
        "outcomes: %d rows, %d unique place_keys across %d sources",
        len(long),
        long["place_key"].nunique(),
        long["source"].nunique(),
    )
    if save:
        settings.results.mkdir(parents=True, exist_ok=True)
        out = settings.results / "outcomes_long.csv"
        long.to_csv(out, index=False)
        log.info("outcomes -> %s", out)
    return long
