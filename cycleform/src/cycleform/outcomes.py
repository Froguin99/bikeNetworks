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


# Canonical 2-letter country code <-> Nominatim-friendly name. Codes for countries
# already in the OECD extract are kept EXACTLY as OECD emits them (UK not GB, KO for
# South Korea, ME for Mexico) so the model's country fixed effect never splits one
# country across two codes; the rest (introduced by ModalShare) use ISO 3166-1
# alpha-2. batch.all_outcome_specs imports this to build geocode queries.
COUNTRY_NAMES: dict[str, str] = {
    "UK": "United Kingdom", "DE": "Germany", "FR": "France", "IT": "Italy",
    "BE": "Belgium", "CH": "Switzerland", "SE": "Sweden", "NO": "Norway",
    "FI": "Finland", "PT": "Portugal", "IE": "Ireland", "US": "United States",
    "CA": "Canada", "AU": "Australia", "JP": "Japan", "CZ": "Czechia",
    "EE": "Estonia", "LV": "Latvia", "SK": "Slovakia", "BG": "Bulgaria",
    "CL": "Chile", "NZ": "New Zealand", "KO": "South Korea", "ME": "Mexico",
    "NL": "Netherlands", "DK": "Denmark", "ES": "Spain", "AT": "Austria",
    "GR": "Greece", "PL": "Poland", "LT": "Lithuania", "SI": "Slovenia",
    "HR": "Croatia", "HU": "Hungary", "RO": "Romania", "CY": "Cyprus",
    "AL": "Albania", "AR": "Argentina", "BD": "Bangladesh", "BY": "Belarus",
    "BR": "Brazil", "CO": "Colombia", "FJ": "Fiji", "GH": "Ghana",
    "HK": "Hong Kong", "IN": "India", "IL": "Israel", "XK": "Kosovo",
    "MY": "Malaysia", "MZ": "Mozambique", "NG": "Nigeria", "PH": "Philippines",
    "SG": "Singapore", "TW": "Taiwan", "UA": "Ukraine", "UY": "Uruguay",
}
_NAME_TO_CODE: dict[str, str] = {name: code for code, name in COUNTRY_NAMES.items()}

# Outcome sources in preference order (best first). Where a place has a cycling rate
# from several sources, prefer_outcome keeps the highest-ranked one. ModalShare is a
# broad, harmonised commute-to-work source (Prieto-Curiel et al.) and takes priority.
SOURCE_PRIORITY: tuple[str, ...] = ("modalshare", "oecd_fua", "legacy_max_value")


def prefer_outcome(df: pd.DataFrame, key: str = "place_key") -> pd.DataFrame:
    """One row per `key`, keeping the highest-priority source (SOURCE_PRIORITY)."""
    if key not in df.columns:
        return df
    if "source" not in df.columns:
        return df.drop_duplicates(key)
    rank = {s: i for i, s in enumerate(SOURCE_PRIORITY)}
    ranked = df.assign(_rank=df["source"].map(lambda s: rank.get(s, len(SOURCE_PRIORITY))))
    ranked = ranked.sort_values("_rank", kind="stable")
    return ranked.drop_duplicates(key).drop(columns="_rank")


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


def load_modalshare(latest_only: bool = True) -> pd.DataFrame:
    """Cycling commute mode share from the ModalShare dataset (Prieto-Curiel et al.,
    github.com/rafaelprietocuriel/ModalShare).

    `Cycling` is the share of commute-to-work trips by bike, stored 0-1 -> scaled to
    %. A harmonised blend of Eurostat, US/CA/AU census, EPOMM, EF China, etc. With
    `latest_only`, keep each city's most recent observation (LastObservation == YES).
    """
    path = settings.external / "cycling_rates" / "modalshare.csv"
    raw = _read_csv_resilient(path)
    d = raw.copy()
    d["Cycling"] = pd.to_numeric(d["Cycling"], errors="coerce")
    d = d[d["Cycling"].notna()]
    if latest_only:
        d = d[d["LastObservation"].astype(str).str.upper() == "YES"]
    out = pd.DataFrame(
        {
            "place_id": d["City"].astype(str),
            "place_key": d["City"].map(place_key),
            "country": d["Country"].map(_NAME_TO_CODE),
            "geom_source": "modalshare",
            "year": pd.to_numeric(d["year"], errors="coerce").astype("Int64"),
            "value": (d["Cycling"] * 100.0).astype(float),
            "numerator": pd.NA,
            "denominator": "commuters (to work)",
            "measure_type": "commute_mode_share",
            "source": "modalshare",
            "sample_n": pd.NA,
            "notes": "ModalShare (Prieto-Curiel et al.); orig: " + d["DataSource"].astype(str),
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
    loaders = (
        ("modalshare", load_modalshare),
        ("oecd_fua", load_oecd_fua),
        ("legacy_max_value", load_max_value),
    )
    for name, loader in loaders:
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
