"""Tests for the head-less query layer used by the MMODA service."""

from __future__ import annotations

import numpy as np
import pytest

from src.data.transient_loader import TransientCatalog
from src.query import (
    FULL_SKY_RADIUS_DEG,
    NoTransientsFound,
    angular_separation_deg,
    filter_catalog,
    ra_deg_to_hours,
    ra_hours_to_deg,
)


def make_catalog(ra_hours, dec_deg, snr_corr=None, dm_corr=None) -> TransientCatalog:
    """Build a synthetic catalog; unspecified columns get harmless values."""
    n = len(ra_hours)
    ones = np.ones(n)
    return TransientCatalog(
        time_from_start=np.arange(n, dtype=float),
        ra=np.asarray(ra_hours, dtype=float),
        dec=np.asarray(dec_deg, dtype=float),
        dm=ones * 10.0,
        snr=ones * 9.0,
        dm_corr=ones * 10.0 if dm_corr is None else np.asarray(dm_corr, dtype=float),
        snr_corr=ones * 9.0 if snr_corr is None else np.asarray(snr_corr, dtype=float),
        tx1000_k=ones * 30.0,
        flux=ones * 20.0,
        flux50=ones * 10.0,
        gl=np.zeros(n),
        gb=np.zeros(n),
    )


class TestUnitConversion:
    def test_hours_to_degrees(self):
        assert ra_hours_to_deg(0.0) == pytest.approx(0.0)
        assert ra_hours_to_deg(12.0) == pytest.approx(180.0)
        assert ra_hours_to_deg(24.0) == pytest.approx(360.0)

    def test_round_trip(self):
        hours = np.array([0.0, 3.5, 11.99, 23.999])
        assert ra_deg_to_hours(ra_hours_to_deg(hours)) == pytest.approx(hours)


class TestAngularSeparation:
    def test_known_separation_on_equator(self):
        catalog = make_catalog([1.0], [0.0])  # RA = 15 deg
        sep = angular_separation_deg(catalog, ra_deg=0.0, dec_deg=0.0)
        assert sep[0] == pytest.approx(15.0, abs=1e-6)

    def test_uses_spherical_not_euclidean_distance(self):
        """Near the pole, a 180 deg RA difference is a tiny angular distance.

        A naive Euclidean distance in the (RA, Dec) plane — which is what the
        desktop click handler uses — would report 180 deg here.
        """
        catalog = make_catalog([12.0], [89.0])  # RA = 180 deg, Dec = +89
        sep = angular_separation_deg(catalog, ra_deg=0.0, dec_deg=89.0)
        assert sep[0] == pytest.approx(2.0, abs=1e-6)

    def test_empty_catalog(self):
        catalog = make_catalog([], [])
        assert angular_separation_deg(catalog, 0.0, 0.0).size == 0


class TestFilterCatalog:
    def test_snr_threshold_is_strict(self):
        catalog = make_catalog([1, 2, 3], [0, 0, 0], snr_corr=[7.9, 8.0, 8.1])
        result = filter_catalog(catalog, snr_min=8.0)
        # 8.0 itself must be excluded, matching main.py's `snr_corr > threshold`
        assert result.source_index.tolist() == [2]

    def test_declination_ceiling(self):
        catalog = make_catalog([1, 2], [70.0, 80.0])
        result = filter_catalog(catalog, dec_max=75.0)
        assert result.source_index.tolist() == [0]

    def test_dm_range(self):
        catalog = make_catalog([1, 2, 3], [0, 0, 0], dm_corr=[5.0, 15.0, 25.0])
        result = filter_catalog(catalog, dm_min=10.0, dm_max=20.0)
        assert result.source_index.tolist() == [1]

    def test_source_index_is_stable_across_queries(self):
        """A transient keeps the same identifier however the query narrows."""
        catalog = make_catalog([1, 2, 3], [0, 0, 0], snr_corr=[9.0, 20.0, 9.0])
        loose = filter_catalog(catalog, snr_min=8.0)
        tight = filter_catalog(catalog, snr_min=15.0)
        assert loose.source_index.tolist() == [0, 1, 2]
        assert tight.source_index.tolist() == [1]
        # The same physical transient, same identifier in both results.
        assert tight.catalog.ra[0] == loose.catalog.ra[1]

    def test_cone_search_selects_neighbours_only(self):
        catalog = make_catalog([0.0, 0.2, 12.0], [0.0, 0.0, 0.0])
        result = filter_catalog(catalog, ra_deg=0.0, dec_deg=0.0, radius_deg=5.0)
        assert result.source_index.tolist() == [0, 1]
        assert result.separation_deg == pytest.approx([0.0, 3.0], abs=1e-6)

    def test_full_sky_radius_skips_positional_filter(self):
        catalog = make_catalog([0.0, 12.0], [0.0, 40.0])
        result = filter_catalog(
            catalog, ra_deg=0.0, dec_deg=0.0, radius_deg=FULL_SKY_RADIUS_DEG
        )
        assert len(result) == 2
        assert result.separation_deg is None

    def test_cone_needs_both_coordinates(self):
        catalog = make_catalog([0.0, 12.0], [0.0, 40.0])
        result = filter_catalog(catalog, ra_deg=0.0, dec_deg=None, radius_deg=1.0)
        assert result.separation_deg is None
        assert len(result) == 2

    def test_n_total_reports_pre_filter_size(self):
        catalog = make_catalog([1, 2, 3], [0, 0, 0], snr_corr=[9.0, 1.0, 1.0])
        result = filter_catalog(catalog, snr_min=8.0)
        assert result.n_total == 3
        assert len(result) == 1

    def test_empty_result_raises_with_helpful_message(self):
        catalog = make_catalog([1, 2], [0, 0], snr_corr=[1.0, 2.0])
        with pytest.raises(NoTransientsFound) as excinfo:
            filter_catalog(catalog, snr_min=8.0)
        message = str(excinfo.value)
        assert "No transients" in message
        assert "SNR_corr > 8.0" in message

    def test_empty_result_message_mentions_the_cone(self):
        catalog = make_catalog([12.0], [0.0])
        with pytest.raises(NoTransientsFound, match="within 1.0 deg"):
            filter_catalog(catalog, ra_deg=0.0, dec_deg=0.0, radius_deg=1.0)
