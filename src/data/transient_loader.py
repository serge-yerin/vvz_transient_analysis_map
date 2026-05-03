"""Loader for the transient CSV file produced by the UTR-2 survey."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

COLUMN_NAMES = [
    "time_from_start",
    "ra",          # right ascension, hours (0..24)
    "dec",         # declination, degrees
    "dm",          # dispersion measure
    "snr",         # signal-to-noise ratio (raw)
    "dm_corr",     # dispersion measure (corrected)
    "snr_corr",    # signal-to-noise ratio (corrected)
    "tx1000_k",    # brightness temperature (Tx1000_K)
    "flux",        # flux S_o, Jy
    "flux50",      # flux S_o50, Jy
]


@dataclass(frozen=True)
class TransientCatalog:
    """Vector of all transients loaded from the CSV. Each field is an ndarray of length N."""

    time_from_start: np.ndarray
    ra: np.ndarray         # hours
    dec: np.ndarray        # degrees
    dm: np.ndarray
    snr: np.ndarray
    dm_corr: np.ndarray
    snr_corr: np.ndarray
    tx1000_k: np.ndarray
    flux: np.ndarray
    flux50: np.ndarray
    gl: np.ndarray = field(default=None)  # galactic longitude, deg (filled later)
    gb: np.ndarray = field(default=None)  # galactic latitude, deg (filled later)

    def __len__(self) -> int:
        return len(self.ra)

    def with_galactic(self, gl: np.ndarray, gb: np.ndarray) -> "TransientCatalog":
        return TransientCatalog(
            time_from_start=self.time_from_start,
            ra=self.ra,
            dec=self.dec,
            dm=self.dm,
            snr=self.snr,
            dm_corr=self.dm_corr,
            snr_corr=self.snr_corr,
            tx1000_k=self.tx1000_k,
            flux=self.flux,
            flux50=self.flux50,
            gl=gl,
            gb=gb,
        )

    def selection(self, mask: np.ndarray) -> "TransientCatalog":
        """Return a new catalog with only the rows where mask is True."""
        return TransientCatalog(
            time_from_start=self.time_from_start[mask],
            ra=self.ra[mask],
            dec=self.dec[mask],
            dm=self.dm[mask],
            snr=self.snr[mask],
            dm_corr=self.dm_corr[mask],
            snr_corr=self.snr_corr[mask],
            tx1000_k=self.tx1000_k[mask],
            flux=self.flux[mask],
            flux50=self.flux50[mask],
            gl=None if self.gl is None else self.gl[mask],
            gb=None if self.gb is None else self.gb[mask],
        )


def _to_float_array(series: pd.Series) -> np.ndarray:
    """Convert a column of strings/floats to floats, tolerating stray internal
    whitespace (e.g. "24 .26") that the IDL pipeline accepts but pandas does not."""
    cleaned = series.astype(str).str.replace(r"\s+", "", regex=True)
    return pd.to_numeric(cleaned, errors="raise").to_numpy(dtype=float)


def load_transients(csv_path: str | Path) -> TransientCatalog:
    """Load the transients CSV. The header line is skipped because the
    original file uses non-ASCII characters in one of the column names."""
    df = pd.read_csv(
        csv_path,
        header=0,
        names=COLUMN_NAMES,
        skipinitialspace=True,
        encoding="latin-1",
    )
    return TransientCatalog(
        time_from_start=_to_float_array(df["time_from_start"]),
        ra=_to_float_array(df["ra"]),
        dec=_to_float_array(df["dec"]),
        dm=_to_float_array(df["dm"]),
        snr=_to_float_array(df["snr"]),
        dm_corr=_to_float_array(df["dm_corr"]),
        snr_corr=_to_float_array(df["snr_corr"]),
        tx1000_k=_to_float_array(df["tx1000_k"]),
        flux=_to_float_array(df["flux"]),
        flux50=_to_float_array(df["flux50"]),
    )
