# UTR-2 transient catalogue

This service queries the catalogue of radio transients detected by the **UTR-2
Pulsar/Transient Survey of the Northern Sky (UTPSNS)** at a central frequency
near 20 MHz, and renders the selection over the 20 MHz galactic background map.

The catalogue contains 380 transients. It is a static, already-published
catalogue: the service does not query a live archive, so results are
reproducible and fast.

## Parameters

| Parameter | Meaning |
|---|---|
| **Source name** | Resolved by MMODA into RA/Dec. Used for the sky map title. |
| **RA**, **Dec** | Centre of the search cone, in degrees (FK5 J2000). |
| **Search radius** | Cone radius in degrees. Leave at **180** to search the whole sky. |
| **Minimum SNR** | Keep transients whose *corrected* signal-to-noise ratio is strictly above this value. |
| **Minimum DM**, **Maximum DM** | Range of *corrected* dispersion measure, in pc/cm³ (inclusive). |

A cone search is applied only when the radius is smaller than 180 degrees.
Otherwise the whole catalogue is returned, filtered by SNR and DM alone.

Separations are true great-circle angular distances, so cone searches remain
correct close to the celestial pole.

## Data products

**`transient_table`** — an astropy table of the matching transients. Every
column carries a unit (where one is defined) and a description, so the
downloaded FITS/VOTable file is self-describing.

| Column | Meaning |
|---|---|
| `TRS` | 1-based row number in the source catalogue. Stable: it does not change when the query changes. |
| `RA`, `DEC` | Position in degrees, FK5 J2000. |
| `RA_hours` | Right ascension in hours, exactly as recorded in the source catalogue. |
| `L`, `B` | Galactic coordinates, degrees. |
| `DM`, `DM_corr` | Dispersion measure, measured and corrected, pc/cm³. |
| `SNR`, `SNR_corr` | Signal-to-noise ratio, measured and corrected. |
| `Tx1000_K` | Brightness temperature in units of 1000 K (see caveat below). |
| `S_o`, `S_o50` | Flux density, Jy. |
| `time_from_start` | Seconds since the start of the observing session (see caveat below). |
| `separation` | Angular distance from the cone centre, degrees. Present only for cone searches; the table is then sorted by it. |

**`sky_map`** — the selected transients as diamonds over the 20 MHz galactic
background. When a cone search is requested, its centre and boundary are marked
in red.

**`histograms`** — distributions of galactic latitude, corrected SNR, flux
density `S_o` and corrected DM, for the selected transients.

**`query_summary`** — a one-line description of what was selected.

## Caveats

**No absolute time.** The source catalogue records only the time elapsed since
the start of each observing session, not the session's absolute date. This
service therefore **cannot be filtered by time**, and MMODA's common `T1`/`T2`
parameters are deliberately not offered. Recovering the absolute epochs is
planned.

**No positional uncertainties.** The catalogue gives nominal positions with no
error radius, so a cone search matches on the nominal position alone. Choose a
radius generous enough to allow for the survey's positional accuracy.

**`Tx1000_K` is a temperature, not a flux.** The original IDL program plots this
column under the label "Flux, Jy". That is a mislabelling — it is a brightness
temperature. The flux density columns are `S_o` and `S_o50`. The exact scaling
of `Tx1000_K` is still to be confirmed with the survey team, which is why the
column carries no unit.

**The background image has no astrometric solution.** It is displayed as a plain
RA/Dec rectangle (RA 24h→0h, Dec −20°→+80°). It is a backdrop for orientation,
not a calibrated map, and should not be used for measurement.

## Empty results

If nothing matches, the service reports which constraints were applied rather
than returning an empty product. Widen the radius or lower the SNR threshold.
