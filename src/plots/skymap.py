"""Head-less rendering of the transient sky map.

This is the non-interactive counterpart of what
`src/gui/main_window.py::_draw_map` draws inside the tkinter window: the same
background and the same markers, but onto a plain `Figure` that can be saved to
a PNG. It never imports pyplot, so it is safe under the `Agg` backend used when
a notebook is executed by papermill.
"""

from __future__ import annotations

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from matplotlib.figure import Figure

from src.data.transient_loader import TransientCatalog
from src.maps.base import BackgroundMap
from src.query import ra_deg_to_hours

#: RA jump (hours) above which a cone outline is assumed to wrap around 0h/24h.
_WRAP_THRESHOLD_H = 12.0


def render_sky_map(
    catalog: TransientCatalog,
    background: BackgroundMap,
    *,
    figure: Figure | None = None,
    cone_center: tuple[float, float] | None = None,
    cone_radius_deg: float | None = None,
    title: str = "UTR-2 transients on the 20 MHz galactic background",
) -> Figure:
    """Draw the transients over the background map and return the figure.

    Parameters
    ----------
    catalog:
        The transients to plot (already filtered).
    background:
        Any :class:`~src.maps.base.BackgroundMap` implementation.
    cone_center:
        ``(ra_deg, dec_deg)`` of the search cone, if one was requested.
    cone_radius_deg:
        Radius of the search cone, in degrees.
    """
    figure = figure or Figure(figsize=(11, 8.5), layout="constrained")
    figure.clear()
    ax = figure.add_subplot(111)

    background.render(ax)
    extent = background.extent
    ax.set_xlim(extent.ra_left, extent.ra_right)  # 24 -> 0 keeps RA increasing leftward
    ax.set_ylim(extent.dec_bottom, extent.dec_top)
    ax.set_xlabel("RA, h")
    ax.set_ylabel("Dec, deg")
    ax.set_xticks(np.arange(0, 25, 4))
    ax.set_yticks(np.arange(-20, 81, 10))
    ax.set_title(title)

    ax.plot(
        catalog.ra,
        catalog.dec,
        marker="D",
        mfc="none",
        mec="black",
        linestyle="none",
        markersize=6,
        markeredgewidth=1.0,
    )

    if cone_center is not None and cone_radius_deg is not None:
        _draw_cone(ax, cone_center, cone_radius_deg)

    return figure


def _draw_cone(ax, center: tuple[float, float], radius_deg: float) -> None:
    """Mark the search cone: a cross at the centre plus its exact outline."""
    ra_deg, dec_deg = center
    ax.plot(
        [ra_deg / 15.0],
        [dec_deg],
        marker="+",
        color="red",
        markersize=14,
        markeredgewidth=2.0,
        linestyle="none",
    )
    for ra_h_seg, dec_seg in _cone_outline(ra_deg, dec_deg, radius_deg):
        ax.plot(ra_h_seg, dec_seg, color="red", linewidth=1.2, linestyle="--")


def _cone_outline(
    ra_deg: float, dec_deg: float, radius_deg: float, n_points: int = 181
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Return the cone boundary as RA-hours/Dec segments, split at the 0h/24h seam.

    The boundary is computed with a real spherical offset rather than an
    ellipse in the (RA, Dec) plane, so it stays correct near the pole where the
    naive `radius / cos(dec)` approximation breaks down.
    """
    center = SkyCoord(
        ra=ra_deg * u.deg, dec=dec_deg * u.deg, frame="fk5", equinox="J2000"
    )
    position_angles = np.linspace(0.0, 360.0, n_points) * u.deg
    boundary = center.directional_offset_by(position_angles, radius_deg * u.deg)

    ra_h = ra_deg_to_hours(boundary.ra.degree)
    dec = boundary.dec.degree

    # Split where the outline crosses RA = 0h/24h so matplotlib does not draw a
    # horizontal line straight across the whole map.
    breaks = np.flatnonzero(np.abs(np.diff(ra_h)) > _WRAP_THRESHOLD_H) + 1
    segments = []
    for ra_seg, dec_seg in zip(
        np.split(ra_h, breaks), np.split(dec, breaks), strict=True
    ):
        if ra_seg.size > 1:
            segments.append((ra_seg, dec_seg))
    return segments
