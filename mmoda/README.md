# MMODA integration

Working notes and plan for exposing the UTR-2 / UTPSNS transient catalog and its
analysis on **MMODA** (Multi-Messenger Online Data Analysis).

This folder is the workspace for that effort. The desktop tkinter application in
the repository root is **not** affected by anything here — it keeps working
exactly as before.

**Status:** first working service notebook, verified end to end with papermill.
Not yet submitted — deployment is still blocked on the hosting question in §6.
**Started:** 2026-07-25. **Target node:** BITP / Kyiv.

---

## 1. Scope: what MMODA is and is not

MMODA is **not a data archive**. You cannot "upload a database" to it. It is a
platform that hosts *parameterized analysis workflows* ("services") which run on
demand and return data products.

That splits our goal into two independent tracks:

| Track | Goal | Where it lives |
|---|---|---|
| **A — Catalog** | Give the catalog a real, citable, VO-queryable archival home | VizieR / CDS (external) |
| **B — Service** | Turn the analysis + plots into an MMODA workflow | this folder |

The two do not block each other. Track A is the durable scientific contribution
and is worth doing regardless of whether Track B ever ships. Track B is what
makes the data *interactive* for other researchers.

---

## 2. How an MMODA service works

A service is a Jupyter notebook with two cells tagged for
[papermill](https://papermill.readthedocs.io/), converted into a containerized
web service by [`nb2workflow`](https://github.com/oda-hub/nb2workflow).

### The `parameters` cell → becomes the web form

```python
# oda:version "v0.1.0"
# oda:reference "https://doi.org/<UTPSNS paper DOI>"

src_name      = "Cas A"   # http://odahub.io/ontology#AstrophysicalObject
RA            = 350.85    # http://odahub.io/ontology#PointOfInterestRA
DEC           = 58.81     # http://odahub.io/ontology#PointOfInterestDEC
radius        = 5.0       # http://odahub.io/ontology#AngleDegrees ; oda:upper_limit 90.
snr_threshold = 8.0       # http://odahub.io/ontology#Float ; oda:lower_limit 5. ;
                          # oda:label "SNR threshold"
```

Annotation notes:

- `oda:` is shorthand for `http://odahub.io/ontology#`.
- Parameters annotated with `PointOfInterestRA` / `PointOfInterestDEC` /
  `AstrophysicalObject` / `StartTime` / `EndTime` are **automatically** rendered
  in MMODA's shared common-parameter header, with the standard names
  `RA`, `DEC`, `src_name`, `T1`, `T2`.
- Constraints: `oda:lower_limit`, `oda:upper_limit`, `oda:allowed_value`, `oda:unit`.
- Presentation: `oda:label` (field title), `oda:description` (tooltip),
  `oda:group` (groups fields horizontally).
- File inputs: `oda:POSIXPath` (upload widget), `oda:FileURL` (URL text field).

### The `outputs` cell → becomes the data products

```python
transient_table = table       # http://odahub.io/ontology#ODAAstropyTable
sky_map         = "map.png"   # http://odahub.io/ontology#ODAPictureProduct
histograms      = "hist.png"  # http://odahub.io/ontology#ODAPictureProduct
```

Outputs may be scalars, arrays, astropy tables, or **filenames** — if a filename
is given, the whole file becomes the product. `WorkflowResultComment` is a
special type rendered as a yellow notice box rather than a downloadable product.

### Execution model — the key constraint

```
web form  →  papermill runs the notebook HEADLESS  →  static products
```

There is **no event loop, no callback, no live window**. Whatever the notebook
produces is what the user sees. This is the single most important fact driving
the design below.

---

## 3. What of the existing code we can reuse

Good news: Tk is already confined to `src/gui/` only (verified — no `pyplot`,
no `tkinter` imports anywhere else). Everything else is headless-safe and
imports cleanly into a notebook.

| Module | Lines | Fate in MMODA |
|---|---|---|
| `src/data/transient_loader.py` | 107 | **Reuse as-is** |
| `src/coordinates/transforms.py` | 54 | **Reuse as-is** (astropy) |
| `src/plots/histograms.py` | 120 | **Reuse** — takes a `Figure`, no pyplot → `fig.savefig()` → `ODAPictureProduct` |
| `src/maps/base.py` | 56 | **Reuse** — `render(ax)` is pure matplotlib |
| `src/maps/jpeg_map.py` | 44 | **Reuse** |
| `src/gui/main_window.py` | 164 | **Drop** — tkinter |
| `src/gui/info_panel.py` | 60 | **Drop** — tkinter |
| `main.py` | 73 | **Rewrite** as the parameters + orchestration cells |

Roughly **75% of the code ports directly**. The `BackgroundMap` abstraction is
exactly the right seam — the notebook just needs a `BackgroundMap` instance and
a `Figure`.

Note: `main.py` calls `matplotlib.use("TkAgg")`. The notebook must **not** do
that — it needs the `Agg` backend (headless). `tests/test_notebook.py` enforces
this.

### Modules added for the service

All head-less, all covered by tests, all usable by the desktop application too:

| Module | Purpose |
|---|---|
| `src/query.py` | Cone search, SNR/DM filtering, RA hours↔degrees conversion, `NoTransientsFound` |
| `src/products.py` | `QueryResult` → annotated astropy `Table` with units and descriptions |
| `src/plots/skymap.py` | Head-less sky map rendering, including an exact cone outline |

---

## 4. Replacing the interactivity

The desktop app's click-to-inspect loop has no MMODA equivalent. It gets
re-expressed as parameters and products, which is closer to MMODA's idiom:

| Desktop app | MMODA service |
|---|---|
| Click a point on the map | **Cone search** — `RA`, `DEC`, `radius` parameters |
| Popup info panel with one transient's parameters | **`ODAAstropyTable`** — full filtered subset, browsable in the frontend and downloadable via `oda_api` |
| Red marker line on histograms | Histograms computed over the *filtered subset* the user selected |
| SNR threshold constant | An exposed form parameter |
| Zoom / pan toolbar | (lost — static PNG) |

The user loses "point and click", and gains "query programmatically, get a real
table back in your own notebook". For a survey catalog that is arguably the more
useful mode.

---

## 5. Open problems to resolve

These are real issues, ordered by how much they matter:

1. **No absolute epoch.** `Time_from_start` is seconds from an *unspecified*
   observation start. MMODA services are normally filterable by `T1`/`T2`, and
   we cannot support that without the observation start dates. This is the
   biggest scientific gap and is worth fixing at the catalog level regardless of
   MMODA. **Needs input from the survey team.**
2. ~~**RA units mismatch.**~~ *Handled 2026-07-26.* The CSV stores RA in
   **hours** (0–24); `PointOfInterestRA` is in **degrees**. All of `src/query.py`
   and `src/products.py` work in degrees, the published table carries both `RA`
   (deg) and `RA_hours`, and `tests/test_products.py` asserts the conversion.
3. **No positional uncertainties.** Cone-search semantics are ill-defined
   without a per-transient error radius. Currently we can only do
   "nearest / within radius of the nominal position".
4. **Background JPEG has no WCS.** `assets/GalBackgr20MHz-1.jpg` is an assumed
   RA/Dec rectangle (RA 24h→0h, Dec −20°→+80°) with no real astrometry. Fine as
   a picture, not acceptable as a VO product. Natural fix: a new
   `BackgroundMap` subclass backed by a real FITS / HEALPix low-frequency sky
   map.
5. **CSV hygiene.** The header line contains non-ASCII characters (the loader
   works around this with `encoding="latin-1"` and skipping the header), and at
   least one value has stray internal whitespace (`"24 .26"`). Clean this before
   anything is published anywhere.
6. **Provenance and credit.** Needs an `oda:reference` DOI for the UTPSNS
   publication, plus `acknowledgements.md` crediting the data providers.
7. **Column semantics.** As already noted in `src/plots/histograms.py`, the IDL
   histogram labelled "Flux, Jy" actually plots `Tx1000_K` (brightness
   temperature), not `S_o`. The Python code deliberately uses `S_o`. Any
   published table must document what each column really is.

8. **Support files must move to the repository root at submission time.** MMODA
   reads `requirements.txt`, `environment.yml`, `mmoda_help_page.md`,
   `acknowledgements.md` and `mmoda.yaml` from the **repository root**. They
   currently live in `mmoda/` so the desktop application's own
   `requirements.txt` stays untouched. See §6 for the exact layout.

9. **`u.hourangle` is not FITS-representable.** Discovered by the round-trip
   test: attaching that unit to `RA_hours` makes `Table.write(..., format="fits")`
   raise `UnitScaleError`, which would have broken the download product. The
   column is therefore published without a unit, with the units stated in its
   description instead.

Non-problem: the catalog is ~25 KB / 380 rows, small enough to ship inside the
repo. MMODA's guidance only warns against embedding *large* datasets.

Non-problem: the default filters (`SNR_corr > 8`, `Dec < 75`) exclude nothing —
all 380 rows pass, because the published catalog is already pre-filtered. A
default run therefore returns the whole catalog, which is a sensible landing
state for the service.

---

## 6. Deployment — and the blocker

The documented path is:

1. Create a project in the `astronomy/mmoda` namespace on **gitlab.renkulab.io**
2. Add notebook + `requirements.txt` / `environment.yml`
3. Test it in an interactive Renku session
4. Add the **`live-workflow`** topic in GitLab project settings
5. A bot scans the namespace, converts the notebook to a service, and deploys it
6. Monitor CI/CD; confirmation arrives by email

### ⚠️ Blocker — verify before writing code

`gitlab.renkulab.io` **stopped accepting new projects** and was slated for
shutdown in **January 2026** (now past). The
[migration issue](https://github.com/oda-hub/hugo-odahub/issues/129) was still
undecided between `gitlab.com/mmoda` and an IN2P3 GitLab instance when last
public, and the official docs may simply be stale.

**Action: email `contact@odahub.io`** and ask:
- Where are new MMODA workflows hosted now, post-Renku-shutdown?
- Can we get namespace access?
- Is the `live-workflow` topic mechanism still how deployment is triggered?
- Do they want the catalog in VizieR first, or is a repo-bundled CSV acceptable?

### Which node to approach

MMODA is **federated** — the same workflows are deployable across several sites:

| Site | URL |
|---|---|
| UNIGE (Geneva) — main | https://www.astro.unige.ch/mmoda/ |
| APC / Paris | https://si-apc.pages.in2p3.fr/face-website/service/mmo/ |
| **BITP / Kyiv** | https://ui.oda.virgoua.org/mmoda/ |

The **Kyiv (BITP) node is worth approaching directly** — UTR-2 is a Ukrainian
instrument, and a local node is the most natural home for a Ukrainian survey
catalog. They may also be more motivated to help push it through than the
general contact address.

Nothing in Track B should be considered final until this is answered.

### Expected repo layout at submission time

MMODA discovers notebooks at repo root by default. Since ours will live in this
subfolder, we need a root-level `mmoda.yaml`:

```yaml
notebook_path: "mmoda"
filename_pattern: "utr2_.*"
```

Other files MMODA looks for (at repo root):

- `requirements.txt` — pip dependencies
- `environment.yml` — conda environment
- `mmoda_help_page.md` — help text shown on the service page
- `acknowledgements.md` — attribution / data provider credits
- `test_*.ipynb` — test notebooks (excluded from becoming services)

---

## 7. What is here, and how to run it

```
mmoda/
├── README.md                 this document
├── utr2_transients.ipynb     the service notebook
├── requirements.txt          service dependencies      -> root at submission
├── environment.yml           conda environment         -> root at submission
├── mmoda.yaml                notebook discovery config -> root at submission
├── mmoda_help_page.md        help text for the service -> root at submission
└── acknowledgements.md       credits                   -> root at submission
```

### One-time setup

```bash
pip install -e .            # makes `src` importable from anywhere
pip install pytest papermill ipykernel nbformat
```

The editable install is what lets the notebook run irrespective of the working
directory. Papermill executes with the *caller's* working directory, not the
notebook's, so relying on relative paths does not work — the notebook falls back
to searching upwards for `src/query.py`, and honours `UTR2_REPO_ROOT` as a last
resort, but installing the package is the clean path.

### Run the tests

```bash
pytest                      # 43 tests, ~20 s (includes 3 real notebook runs)
pytest -m "not slow"        # skip the papermill executions
```

### Run the notebook by hand

```bash
# whole sky
papermill mmoda/utr2_transients.ipynb /tmp/out.ipynb -k python3

# cone search around Cas A
papermill mmoda/utr2_transients.ipynb /tmp/out.ipynb -k python3 \
    -p src_name "Cas A" -p RA 350.85 -p DEC 58.815 -p radius 20.0
```

It writes `utr2_sky_map.png` and `utr2_histograms.png` into the working
directory. Both filenames are git-ignored.

### The parameters it exposes

| Parameter | Default | Ontology type |
|---|---|---|
| `src_name` | `"Cas A"` | `AstrophysicalObject` |
| `RA` | `350.85` | `PointOfInterestRA` |
| `DEC` | `58.815` | `PointOfInterestDEC` |
| `radius` | `180.0` | `AngleDegrees` (180 = whole sky) |
| `snr_threshold` | `8.0` | `Float` |
| `dm_min` / `dm_max` | `0.0` / `100.0` | `Float` |

### The products it returns

| Output | Ontology type |
|---|---|
| `transient_table` | `ODAAstropyTable` |
| `sky_map` | `ODAPictureProduct` |
| `histograms` | `ODAPictureProduct` |
| `query_summary` | `WorkflowResultComment` |

---

## 8. Plan

### Track A — Catalog (independent, do regardless)

- [ ] Recover absolute observation epochs for `Time_from_start`
- [ ] Add per-transient positional uncertainties (if recoverable)
- [ ] Clean the CSV: ASCII header, fix stray whitespace, document every column
- [ ] Write a column-by-column data dictionary with units
- [ ] Prepare and submit the VizieR/CDS package
- [ ] Obtain / confirm the UTPSNS publication DOI

### Track B — MMODA service

- [ ] **Contact the BITP/Kyiv node** (§6) — target node, likeliest ally ← *do this first*
- [ ] Email `contact@odahub.io` — resolve the hosting blocker (§6)
- [x] Draft `utr2_transients.ipynb`: parameters cell, orchestration, outputs cell
- [x] Cone-search + SNR/DM filtering helper — `src/query.py`
- [x] RA hours ↔ degrees conversion, with a test
- [x] Headless figure rendering: histograms → PNG, sky map → PNG
- [x] Build the `ODAAstropyTable` output with proper units and column metadata
- [x] `requirements.txt` / `environment.yml` for the service container
- [x] `mmoda_help_page.md` and `acknowledgements.md`
- [x] `mmoda.yaml` (template in `mmoda/`, to be moved to root)
- [x] Verify end to end with papermill, including parameter injection
- [ ] Fill in the real `oda:reference` DOI (currently a placeholder in the notebook)
- [ ] `test_utr2_transients.ipynb` using `nb2workflow.nbadapter.run` — MMODA wants a
      notebook-form test for its automated monitoring, alongside our pytest suite
- [ ] Install `nb2workflow` and validate the annotations it actually parses
- [ ] Move the support files to the repository root (§5.8)
- [ ] Local run via `nb2service`, then `nb2worker` container build
- [ ] Deploy, verify in the MMODA frontend, supply test parameters to the team

### Nice to have / later

- [ ] `FitsBackgroundMap` — real WCS sky map replacing the JPEG (fixes §5.4)
- [ ] Support `T1`/`T2` time filtering (needs §5.1 resolved)
- [ ] Expose the catalog through a VO TAP service

---

## 9. Work log

Newest first. One entry per session — what was done, what was decided, what is
next.

### 2026-07-26 — First working service notebook

- **Decided:** target the **BITP/Kyiv** node.
- Built the head-less analysis layer: `src/query.py`, `src/products.py`,
  `src/plots/skymap.py`. No existing file was modified, so the desktop
  application is untouched (re-checked: still 380 → 380).
- Wrote `mmoda/utr2_transients.ipynb` with `parameters` and `outputs` cells,
  plus the support files listed in §7.
- Added `pyproject.toml` and 43 tests. **Two real bugs were caught by tests:**
  - `u.hourangle` cannot be written to FITS — would have broken the download
    product (§5.9);
  - papermill executes with the *caller's* working directory, so the notebook's
    original path discovery failed from an unrelated directory. Fixed by making
    the project pip-installable, with a search-upwards fallback.
- Verified end to end with papermill from an unrelated directory: whole-sky run
  returns 380/380; a 20° cone around Cas A returns 10/380; an impossible query
  fails with the intended explanatory message.
- **Next:** contact the Kyiv node. Then the real DOI, the `test_*.ipynb`, and
  validation against `nb2workflow` itself.

### 2026-07-25 — Feasibility study

- Studied the MMODA manifesto, the ODA development guide, `nb2workflow`, and the
  ODA ontology.
- **Established:** MMODA hosts workflows, not datasets. "Just upload the
  database" is not an option the platform offers.
- **Established:** the tkinter GUI cannot be ported; MMODA runs notebooks
  headless. Interactivity must be re-expressed as form parameters + products.
- **Established:** ~75% of the existing code is directly reusable because Tk is
  already isolated in `src/gui/`.
- **Found blocker:** the documented Renku GitLab hosting path is defunct as of
  January 2026 and the replacement is not publicly settled.
- **Found:** MMODA is federated across three public nodes, one of which is
  BITP/Kyiv — a promising direct contact for a Ukrainian survey catalog.
- Created this folder and document. No code written yet.
- **Next:** email `contact@odahub.io` before investing implementation effort.

---

## 10. References

| What | Link |
|---|---|
| MMODA manifesto | https://github.com/oda-hub/mmoda-manifesto |
| ODA development guide (the key document) | https://odahub.io/docs/guide-development/ |
| ODA discovery guide | https://odahub.io/docs/guide-discovery/ |
| ODA ontology guide | https://odahub.io/docs/guide-ontology/ |
| ODA ontology browser | https://odahub.io/ontology/ |
| `nb2workflow` | https://github.com/oda-hub/nb2workflow |
| `oda_api` | https://github.com/oda-hub/oda_api |
| MMODA frontend — UNIGE (main) | https://www.astro.unige.ch/mmoda/ |
| MMODA frontend — APC/Paris | https://si-apc.pages.in2p3.fr/face-website/service/mmo/ |
| MMODA frontend — BITP/Kyiv | https://ui.oda.virgoua.org/mmoda/ |
| ODA France branch | https://odahub.fr/ |
| Renku GitLab migration issue | https://github.com/oda-hub/hugo-odahub/issues/129 |
| Galaxy tutorial (nb2workflow conventions) | https://my.galaxy.training/training-material/topics/dev/tutorials/tool-from-notebook/tutorial.html |
| Contact | `contact@odahub.io` |
