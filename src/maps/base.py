"""Abstract base class for sky background maps.

The application currently uses a JPEG of the 20 MHz galactic background
(equatorial RA/Dec axes, no real WCS). In the future we may want to plug in
higher-resolution images or proper FITS files with WCS information. The
contract a map has to fulfill is small enough to support that.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
from matplotlib.axes import Axes


@dataclass(frozen=True)
class MapExtent:
    """Coordinate ranges covered by the map (in the same units as the data being plotted).

    For the current map: RA in hours, Dec in degrees. The convention follows
    matplotlib `imshow` extent: (left, right, bottom, top).
    """
    ra_left: float    # RA at the left edge of the image, hours
    ra_right: float   # RA at the right edge of the image, hours
    dec_bottom: float # Dec at the bottom edge, degrees
    dec_top: float    # Dec at the top edge, degrees

    def as_imshow_extent(self) -> tuple[float, float, float, float]:
        return (self.ra_left, self.ra_right, self.dec_bottom, self.dec_top)


class BackgroundMap(ABC):
    """A sky background map that can be rendered onto a matplotlib axis."""

    @property
    @abstractmethod
    def extent(self) -> MapExtent: ...

    @property
    @abstractmethod
    def image(self) -> np.ndarray:
        """Return the image array (2D grayscale or 3D RGB)."""

    def render(self, ax: Axes) -> None:
        """Draw the map on the given axis. Subclasses can override for custom styling."""
        ax.imshow(
            self.image,
            extent=self.extent.as_imshow_extent(),
            origin="upper",
            aspect="auto",
            cmap="gray",
            vmin=0,
            vmax=255,
        )
