"""Equatorial <-> Galactic coordinate transformations.

Replacement for the IDL `glactc` routine. We rely on astropy's well-tested
implementation, which internally takes care of FK5 J2000 -> FK4 B1950 -> Galactic
precession exactly like `glactc` does.
"""

from __future__ import annotations

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord


def equatorial_to_galactic(
    ra_hours: np.ndarray,
    dec_deg: np.ndarray,
    equinox: str = "J2000",
) -> tuple[np.ndarray, np.ndarray]:
    """Convert FK5 equatorial coordinates to galactic (l, b).

    Parameters
    ----------
    ra_hours : array-like
        Right ascension, in HOURS (0..24), as in the source CSV.
    dec_deg : array-like
        Declination, in degrees.
    equinox : str
        Equinox of the input coordinates. Default 'J2000' to match the IDL code.

    Returns
    -------
    gl, gb : ndarray
        Galactic longitude and latitude, in degrees.
    """
    ra_deg = np.asarray(ra_hours, dtype=float) * 15.0
    dec_deg = np.asarray(dec_deg, dtype=float)
    coord = SkyCoord(
        ra=ra_deg * u.deg,
        dec=dec_deg * u.deg,
        frame="fk5",
        equinox=equinox,
    )
    gal = coord.galactic
    return gal.l.degree, gal.b.degree


def hours_to_hms(ra_hours: float) -> tuple[int, int, float]:
    """Split a decimal RA in hours into (h, m, s)."""
    hours_int = int(np.floor(ra_hours))
    rem_min = (ra_hours - hours_int) * 60.0
    minutes_int = int(np.floor(rem_min))
    seconds = (rem_min - minutes_int) * 60.0
    return hours_int, minutes_int, seconds
