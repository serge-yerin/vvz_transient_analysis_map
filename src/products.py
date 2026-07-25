"""Build the MMODA data products (astropy tables) from a catalog query.

Kept free of matplotlib and GUI imports so it is safe to use inside a
head-lessly executed notebook.
"""

from __future__ import annotations

import numpy as np
from astropy import units as u
from astropy.table import Table

from src.query import QueryResult, ra_hours_to_deg

#: Human-readable meaning of every column we publish. These end up in the
#: table metadata and in the MMODA help page, so a user who downloads the
#: product knows what each number is without reading our source.
COLUMN_DESCRIPTIONS = {
    "TRS": "Transient identifier: 1-based row number in the source UTPSNS catalogue",
    "RA": "Right ascension, FK5 J2000",
    "DEC": "Declination, FK5 J2000",
    "RA_hours": (
        "Right ascension in hours (0-24), exactly as recorded in the source "
        "catalogue, for cross-referencing. Carries no astropy unit because "
        "'hourangle' has no FITS representation; use RA for the standard "
        "degrees value."
    ),
    "L": "Galactic longitude",
    "B": "Galactic latitude",
    "DM": "Dispersion measure, as measured",
    "DM_corr": "Dispersion measure, corrected",
    "SNR": "Signal-to-noise ratio, as measured",
    "SNR_corr": "Signal-to-noise ratio, corrected",
    "Tx1000_K": (
        "Brightness temperature in units of 1000 K, as recorded by the survey "
        "pipeline. NOTE: the original IDL program plots this column under the "
        "label 'Flux, Jy', which is a mislabelling - it is a temperature, not a "
        "flux density. Units to be confirmed with the survey team."
    ),
    "S_o": "Flux density of the transient",
    "S_o50": "Flux density at 50 per cent level",
    "time_from_start": (
        "Time elapsed since the start of the observation session. The absolute "
        "epoch of that start is not recorded in the source catalogue, so this "
        "column cannot currently be converted to an absolute date."
    ),
    "separation": "Angular distance from the centre of the requested search cone",
}

#: Units for the columns where we are confident of them. RA_hours is
#: deliberately absent: `u.hourangle` cannot be written to FITS, which would
#: break the downloadable product.
COLUMN_UNITS = {
    "RA": u.deg,
    "DEC": u.deg,
    "L": u.deg,
    "B": u.deg,
    "DM": u.pc / u.cm**3,
    "DM_corr": u.pc / u.cm**3,
    "S_o": u.Jy,
    "S_o50": u.Jy,
    "time_from_start": u.s,
    "separation": u.deg,
}


def query_to_table(result: QueryResult, meta: dict | None = None) -> Table:
    """Convert a :class:`~src.query.QueryResult` into an annotated astropy Table.

    The table carries units and per-column descriptions, so it survives the
    round trip to FITS/VOTable and stays self-describing after download.
    """
    catalog = result.catalog
    columns: dict[str, np.ndarray] = {
        "TRS": result.source_index + 1,
        "RA": ra_hours_to_deg(catalog.ra),
        "DEC": np.asarray(catalog.dec, dtype=float),
        "RA_hours": np.asarray(catalog.ra, dtype=float),
    }
    if catalog.gl is not None:
        columns["L"] = np.asarray(catalog.gl, dtype=float)
    if catalog.gb is not None:
        columns["B"] = np.asarray(catalog.gb, dtype=float)
    columns.update(
        {
            "DM": catalog.dm,
            "DM_corr": catalog.dm_corr,
            "SNR": catalog.snr,
            "SNR_corr": catalog.snr_corr,
            "Tx1000_K": catalog.tx1000_k,
            "S_o": catalog.flux,
            "S_o50": catalog.flux50,
            "time_from_start": catalog.time_from_start,
        }
    )
    if result.separation_deg is not None:
        columns["separation"] = result.separation_deg

    table = Table(columns)
    for name in table.colnames:
        if name in COLUMN_UNITS:
            table[name].unit = COLUMN_UNITS[name]
        if name in COLUMN_DESCRIPTIONS:
            table[name].description = COLUMN_DESCRIPTIONS[name]

    table.meta.update(
        {
            "SURVEY": "UTR-2 Pulsar/Transient Survey of the Northern Sky (UTPSNS)",
            "TELESCOP": "UTR-2",
            "EQUINOX": "J2000",
            "RADESYS": "FK5",
            "N_TOTAL": result.n_total,
            "N_SELECT": len(result),
        }
    )
    if meta:
        table.meta.update(meta)

    if result.separation_deg is not None:
        table.sort("separation")
    return table
