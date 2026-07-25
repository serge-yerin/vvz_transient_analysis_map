"""Headless catalog querying: unit conversion, cone search and parameter filters.

Everything here is free of GUI and matplotlib imports so it can be used from a
notebook executed head-less by papermill (see `mmoda/`), as well as from the
desktop application.

Note on units: the source CSV stores RA in **hours** (0..24), while MMODA's
common `RA` parameter — and virtually every other astronomical service — uses
**degrees**. All public functions in this module take and return degrees; the
hours convention stops at the loader.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord

from src.data.transient_loader import TransientCatalog

#: A cone this large covers the whole sky, i.e. "no positional filtering".
FULL_SKY_RADIUS_DEG = 180.0


class NoTransientsFound(Exception):
    """Raised when a query selects no transients at all.

    MMODA renders the message of a raised exception to the user, so the text
    should read as an explanation rather than as a stack trace.
    """


def ra_hours_to_deg(ra_hours) -> np.ndarray:
    """Convert right ascension from hours (the CSV convention) to degrees."""
    return np.asarray(ra_hours, dtype=float) * 15.0


def ra_deg_to_hours(ra_deg) -> np.ndarray:
    """Convert right ascension from degrees to hours (the CSV convention)."""
    return np.asarray(ra_deg, dtype=float) / 15.0


def catalog_skycoord(catalog: TransientCatalog) -> SkyCoord:
    """FK5 J2000 SkyCoord for every entry of the catalog."""
    return SkyCoord(
        ra=ra_hours_to_deg(catalog.ra) * u.deg,
        dec=np.asarray(catalog.dec, dtype=float) * u.deg,
        frame="fk5",
        equinox="J2000",
    )


def angular_separation_deg(
    catalog: TransientCatalog, ra_deg: float, dec_deg: float
) -> np.ndarray:
    """Great-circle distance in degrees from each transient to (ra_deg, dec_deg).

    Uses a real spherical separation, not a Euclidean distance in the
    (RA, Dec) plane — the latter is what the desktop application's click
    handler does, which is acceptable for picking a point under the cursor but
    wrong as a scientific cone search away from the equator.
    """
    if len(catalog) == 0:
        return np.empty(0, dtype=float)
    reference = SkyCoord(
        ra=float(ra_deg) * u.deg,
        dec=float(dec_deg) * u.deg,
        frame="fk5",
        equinox="J2000",
    )
    return catalog_skycoord(catalog).separation(reference).degree


@dataclass(frozen=True)
class QueryResult:
    """The outcome of :func:`filter_catalog`.

    Attributes
    ----------
    catalog:
        The transients that passed every filter.
    source_index:
        0-based row numbers of those transients in the *original* catalog.
        These are stable identifiers: unlike a position in the filtered list,
        they do not change when the query parameters change. ``TRS #`` as
        displayed by the desktop application is ``source_index + 1``.
    separation_deg:
        Angular distance to the cone centre, or ``None`` when no cone search
        was requested.
    n_total:
        Size of the catalog before filtering, for reporting.
    """

    catalog: TransientCatalog
    source_index: np.ndarray
    separation_deg: np.ndarray | None
    n_total: int

    def __len__(self) -> int:
        return len(self.catalog)


def filter_catalog(
    catalog: TransientCatalog,
    *,
    ra_deg: float | None = None,
    dec_deg: float | None = None,
    radius_deg: float = FULL_SKY_RADIUS_DEG,
    snr_min: float = 8.0,
    dm_min: float | None = None,
    dm_max: float | None = None,
    dec_max: float | None = 75.0,
) -> QueryResult:
    """Select transients by position and by physical parameters.

    All angles are in degrees. A cone search is applied only when both
    ``ra_deg`` and ``dec_deg`` are given and ``radius_deg`` is smaller than the
    whole sky; otherwise the positional filter is skipped and
    ``separation_deg`` is ``None``.

    ``snr_min`` and ``dec_max`` reproduce the desktop application's defaults
    (``snr_corr > 8`` and ``dec < 75``) including their strict comparisons, so
    the same subset comes out for the same numbers.

    Raises
    ------
    NoTransientsFound
        If nothing passes the filters.
    """
    n_total = len(catalog)
    mask = np.ones(n_total, dtype=bool)

    if snr_min is not None:
        mask &= catalog.snr_corr > snr_min
    if dec_max is not None:
        mask &= catalog.dec < dec_max
    if dm_min is not None:
        mask &= catalog.dm_corr >= dm_min
    if dm_max is not None:
        mask &= catalog.dm_corr <= dm_max

    cone_requested = (
        ra_deg is not None
        and dec_deg is not None
        and radius_deg is not None
        and radius_deg < FULL_SKY_RADIUS_DEG
    )
    separation_all = None
    if cone_requested:
        separation_all = angular_separation_deg(catalog, ra_deg, dec_deg)
        mask &= separation_all <= radius_deg

    source_index = np.flatnonzero(mask)
    if source_index.size == 0:
        raise NoTransientsFound(_no_result_message(locals()))

    return QueryResult(
        catalog=catalog.selection(mask),
        source_index=source_index,
        separation_deg=None if separation_all is None else separation_all[mask],
        n_total=n_total,
    )


def _no_result_message(ctx: dict) -> str:
    """Build a human-readable explanation of an empty query."""
    parts = [f"SNR_corr > {ctx['snr_min']}"]
    if ctx.get("dec_max") is not None:
        parts.append(f"Dec < {ctx['dec_max']} deg")
    if ctx.get("dm_min") is not None:
        parts.append(f"DM_corr >= {ctx['dm_min']}")
    if ctx.get("dm_max") is not None:
        parts.append(f"DM_corr <= {ctx['dm_max']}")
    if ctx.get("cone_requested"):
        parts.append(
            f"within {ctx['radius_deg']} deg of "
            f"RA={ctx['ra_deg']} deg, Dec={ctx['dec_deg']} deg"
        )
    return (
        "No transients in the UTR-2 catalogue match this query ("
        + "; ".join(parts)
        + "). Try relaxing the SNR threshold or widening the search radius."
    )
