"""Tests for head-less sky map rendering.

These use the `Agg` backend explicitly, the same way the MMODA notebook does,
to prove nothing in the drawing path needs a display.
"""

from __future__ import annotations

import matplotlib
import numpy as np
import pytest

matplotlib.use("Agg")

from src.maps.base import BackgroundMap, MapExtent  # noqa: E402
from src.plots.skymap import _cone_outline, render_sky_map  # noqa: E402
from tests.test_query import make_catalog  # noqa: E402


class FakeBackground(BackgroundMap):
    """A tiny uniform background, so tests do not depend on the JPEG asset."""

    @property
    def extent(self) -> MapExtent:
        return MapExtent(ra_left=24.0, ra_right=0.0, dec_bottom=-20.0, dec_top=80.0)

    @property
    def image(self) -> np.ndarray:
        return np.full((10, 20), 128, dtype=np.uint8)


class TestRenderSkyMap:
    def test_produces_a_figure_with_markers(self):
        catalog = make_catalog([1.0, 12.0, 23.0], [0.0, 40.0, 70.0])
        figure = render_sky_map(catalog, FakeBackground())
        ax = figure.axes[0]
        # One image (background) plus one marker line.
        assert len(ax.images) == 1
        assert len(ax.lines) == 1
        assert ax.lines[0].get_xdata() == pytest.approx([1.0, 12.0, 23.0])

    def test_ra_axis_is_inverted(self):
        figure = render_sky_map(make_catalog([1.0], [0.0]), FakeBackground())
        left, right = figure.axes[0].get_xlim()
        assert left == 24.0 and right == 0.0

    def test_saves_to_png_without_a_display(self, tmp_path):
        figure = render_sky_map(make_catalog([1.0], [0.0]), FakeBackground())
        path = tmp_path / "map.png"
        figure.savefig(path, dpi=60)
        assert path.stat().st_size > 0

    def test_cone_is_drawn_when_requested(self):
        figure = render_sky_map(
            make_catalog([1.0], [0.0]),
            FakeBackground(),
            cone_center=(15.0, 0.0),
            cone_radius_deg=5.0,
        )
        # markers + centre cross + at least one outline segment
        assert len(figure.axes[0].lines) >= 3


class TestConeOutline:
    def test_outline_lies_on_the_requested_radius(self):
        from astropy import units as u
        from astropy.coordinates import SkyCoord

        ra_deg, dec_deg, radius = 60.0, 30.0, 8.0
        center = SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg, frame="fk5")
        for ra_h, dec in _cone_outline(ra_deg, dec_deg, radius):
            points = SkyCoord(ra=ra_h * 15.0 * u.deg, dec=dec * u.deg, frame="fk5")
            assert points.separation(center).degree == pytest.approx(radius, abs=1e-6)

    def test_outline_is_split_at_the_ra_seam(self):
        """A cone straddling RA = 0h must not be drawn as one line across the map."""
        segments = _cone_outline(ra_deg=0.0, dec_deg=0.0, radius_deg=10.0)
        assert len(segments) > 1
        for ra_h, _dec in segments:
            assert np.all(np.abs(np.diff(ra_h)) < 12.0)

    def test_outline_away_from_the_seam_is_continuous(self):
        segments = _cone_outline(ra_deg=180.0, dec_deg=0.0, radius_deg=10.0)
        assert len(segments) == 1

    def test_circumpolar_cone_does_not_blow_up(self):
        """Near the pole the naive radius/cos(dec) approximation diverges."""
        segments = _cone_outline(ra_deg=0.0, dec_deg=89.0, radius_deg=5.0)
        all_dec = np.concatenate([d for _ra, d in segments])
        assert all_dec.max() <= 90.0 + 1e-9
        assert all_dec.min() >= 84.0 - 1e-6
