"""JPEG-backed implementation of BackgroundMap (the original 20 MHz galactic background)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from src.maps.base import BackgroundMap, MapExtent


class JpegBackgroundMap(BackgroundMap):
    """A simple grayscale JPEG that covers a known RA/Dec rectangle.

    The original IDL code lays the image out so that:
      * left edge  -> RA = 24h, right edge -> RA = 0h
      * bottom edge -> Dec = -20 deg, top edge -> Dec = 80 deg
    """

    def __init__(
        self,
        image_path: str | Path,
        extent: MapExtent = MapExtent(
            ra_left=24.0, ra_right=0.0, dec_bottom=-20.0, dec_top=80.0
        ),
        brightness: float = 0.5,
        offset: int = 127,
    ) -> None:
        with Image.open(image_path) as img:
            arr = np.asarray(img.convert("L"), dtype=np.float32)
        # Match the IDL `GalBackgr/2.+127` brightness adjustment so the markers
        # remain visible on top of the map.
        arr = np.clip(arr * brightness + offset, 0, 255).astype(np.uint8)
        self._image = arr
        self._extent = extent

    @property
    def extent(self) -> MapExtent:
        return self._extent

    @property
    def image(self) -> np.ndarray:
        return self._image
