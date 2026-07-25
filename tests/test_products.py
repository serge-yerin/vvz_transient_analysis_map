"""Tests for the astropy table product handed to MMODA."""

from __future__ import annotations

import numpy as np
import pytest
from astropy import units as u

from src.products import query_to_table
from src.query import filter_catalog
from tests.test_query import make_catalog


class TestQueryToTable:
    def test_columns_and_row_count(self):
        catalog = make_catalog([1.0, 2.0], [10.0, 20.0])
        table = query_to_table(filter_catalog(catalog))
        assert len(table) == 2
        for name in ("TRS", "RA", "DEC", "RA_hours", "SNR_corr", "S_o"):
            assert name in table.colnames

    def test_ra_is_published_in_degrees(self):
        """The CSV stores hours; the published product must be degrees."""
        catalog = make_catalog([6.0], [0.0])
        table = query_to_table(filter_catalog(catalog))
        assert table["RA"][0] == pytest.approx(90.0)
        assert table["RA"].unit == u.deg
        # The original hours value stays available alongside it, deliberately
        # without a unit because `hourangle` is not FITS-representable.
        assert table["RA_hours"][0] == pytest.approx(6.0)
        assert table["RA_hours"].unit is None

    def test_trs_identifier_is_one_based_source_row(self):
        catalog = make_catalog([1, 2, 3], [0, 0, 0], snr_corr=[1.0, 9.0, 9.0])
        table = query_to_table(filter_catalog(catalog, snr_min=8.0))
        # Rows 1 and 2 (0-based) survive, so TRS numbers are 2 and 3.
        assert table["TRS"].tolist() == [2, 3]

    def test_units_are_attached(self):
        catalog = make_catalog([1.0], [0.0])
        table = query_to_table(filter_catalog(catalog))
        assert table["DEC"].unit == u.deg
        assert table["S_o"].unit == u.Jy
        assert table["DM_corr"].unit == u.pc / u.cm**3
        assert table["time_from_start"].unit == u.s

    def test_every_column_is_described(self):
        catalog = make_catalog([1.0], [0.0])
        table = query_to_table(
            filter_catalog(catalog, ra_deg=15.0, dec_deg=0.0, radius_deg=10.0)
        )
        undescribed = [c for c in table.colnames if not table[c].description]
        assert undescribed == []

    def test_metadata_records_selection_size(self):
        catalog = make_catalog([1, 2, 3], [0, 0, 0], snr_corr=[1.0, 9.0, 9.0])
        table = query_to_table(filter_catalog(catalog, snr_min=8.0))
        assert table.meta["N_TOTAL"] == 3
        assert table.meta["N_SELECT"] == 2
        assert table.meta["TELESCOP"] == "UTR-2"

    def test_cone_search_adds_sorted_separation_column(self):
        catalog = make_catalog([0.4, 0.0, 0.2], [0.0, 0.0, 0.0])
        table = query_to_table(
            filter_catalog(catalog, ra_deg=0.0, dec_deg=0.0, radius_deg=20.0)
        )
        assert "separation" in table.colnames
        assert table["separation"].unit == u.deg
        # Nearest first.
        assert np.all(np.diff(table["separation"]) >= 0)
        assert table["TRS"][0] == 2  # the entry at RA = 0h

    def test_no_separation_column_without_cone(self):
        table = query_to_table(filter_catalog(make_catalog([1.0], [0.0])))
        assert "separation" not in table.colnames

    def test_extra_meta_is_merged(self):
        table = query_to_table(
            filter_catalog(make_catalog([1.0], [0.0])), meta={"REQUEST": "test"}
        )
        assert table.meta["REQUEST"] == "test"

    def test_survives_fits_round_trip(self, tmp_path):
        """Units and values must survive the format MMODA hands to users."""
        from astropy.table import Table

        catalog = make_catalog([1.0, 2.0], [10.0, 20.0])
        table = query_to_table(filter_catalog(catalog))
        path = tmp_path / "product.fits"
        table.write(path, format="fits")
        reloaded = Table.read(path)
        assert reloaded["RA"][0] == pytest.approx(table["RA"][0])
        assert reloaded["S_o"].unit == u.Jy
