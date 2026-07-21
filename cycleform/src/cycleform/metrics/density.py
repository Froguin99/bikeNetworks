"""Area-based density metrics (per km2).

The user asked for street / intersection / bicycle-network density both per unit
area AND normalised by street-network length. The network-length versions live
elsewhere (intersection_density_per_km in structural.py, cycle-to-road length
ratio bikeable_length_share in relational.py); these are the classic per-km2
densities. They are PlaceMetrics because they need the boundary area.

CAVEAT: area is `built_up_area_km2`, currently the *geocoded boundary* area, not
GHSL built-up land -- so it overstates the denominator and these densities are
provisional (see ASSUMPTIONS.md). Compare with the network-length-normalised
versions, which do not depend on area.
"""

from __future__ import annotations

from cycleform.metrics.base import PlaceContext
from cycleform.metrics.registry import place_metric


@place_metric("street_density_km2", requires={"road"})
def street_density_km2(ctx: PlaceContext) -> float:
    """Road-network length (km) per km2 of boundary area."""
    return (ctx.road.length_total_m / 1000.0) / ctx.built_up_area_km2


@place_metric("cycle_network_density_km2", requires={"bike"})
def cycle_network_density_km2(ctx: PlaceContext) -> float:
    """Cycle-network length (km) per km2 of boundary area."""
    return (ctx.bike.length_total_m / 1000.0) / ctx.built_up_area_km2


@place_metric("intersection_density_km2_road", requires={"road"})
def intersection_density_km2_road(ctx: PlaceContext) -> float:
    """Road intersections (degree >= 3) per km2 of boundary area."""
    return ctx.road.intersection_count / ctx.built_up_area_km2


@place_metric("intersection_density_km2_bike", requires={"bike"})
def intersection_density_km2_bike(ctx: PlaceContext) -> float:
    """Cycle-network intersections (degree >= 3) per km2 of boundary area."""
    return ctx.bike.intersection_count / ctx.built_up_area_km2
