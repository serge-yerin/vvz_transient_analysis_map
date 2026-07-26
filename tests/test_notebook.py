"""Tests for the MMODA service notebook.

The structural tests guard the conventions nb2workflow relies on: without the
`parameters` and `outputs` tags, and without the ontology annotations, the
notebook silently stops being a valid MMODA service. The execution test is
slower and is skipped when papermill is not installed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

nbformat = pytest.importorskip("nbformat")

NOTEBOOK = Path(__file__).resolve().parent.parent / "mmoda" / "utr2_transients.ipynb"

EXPECTED_PARAMETERS = {
    "src_name",
    "RA",
    "DEC",
    "radius",
    "snr_threshold",
    "dm_min",
    "dm_max",
}

EXPECTED_OUTPUTS = {
    "transient_table": "ODAAstropyTable",
    "sky_map": "ODAPictureProduct",
    "histograms": "ODAPictureProduct",
    "query_summary": "WorkflowResultComment",
}


@pytest.fixture(scope="module")
def notebook():
    assert NOTEBOOK.exists(), f"{NOTEBOOK} is missing"
    return nbformat.read(str(NOTEBOOK), as_version=4)


def cell_with_tag(nb, tag: str):
    matches = [c for c in nb.cells if tag in c.get("metadata", {}).get("tags", [])]
    assert len(matches) == 1, f"expected exactly one cell tagged {tag!r}, got {len(matches)}"
    return matches[0]


class TestNotebookStructure:
    def test_is_valid_nbformat(self, notebook):
        nbformat.validate(notebook)

    def test_has_a_parameters_cell(self, notebook):
        source = cell_with_tag(notebook, "parameters").source
        for name in EXPECTED_PARAMETERS:
            assert f"{name} =" in source, f"{name} is not defined in the parameters cell"

    def test_common_parameters_use_the_mmoda_ontology(self, notebook):
        """RA/DEC/src_name must be annotated so MMODA renders its shared header."""
        source = cell_with_tag(notebook, "parameters").source
        for annotation in (
            "PointOfInterestRA",
            "PointOfInterestDEC",
            "AstrophysicalObject",
            "AngleDegrees",
        ):
            assert annotation in source

    def test_notebook_level_annotations_present(self, notebook):
        source = cell_with_tag(notebook, "parameters").source
        assert "oda:version" in source
        assert "oda:reference" in source

    def test_outputs_cell_declares_typed_products(self, notebook):
        source = cell_with_tag(notebook, "outputs").source
        for name, owl_type in EXPECTED_OUTPUTS.items():
            assert f"{name} =" in source, f"{name} is not assigned in the outputs cell"
            line = next(ln for ln in source.splitlines() if ln.startswith(f"{name} ="))
            assert owl_type in line, f"{name} is not annotated as {owl_type}"

    def test_outputs_cell_is_last(self, notebook):
        """nb2workflow collects the outputs cell after everything has run."""
        assert notebook.cells[-1] is cell_with_tag(notebook, "outputs")

    def test_uses_a_headless_backend(self, notebook):
        """Selecting a GUI backend would make the notebook fail in the container.

        Comments are stripped first, so prose mentioning TkAgg does not trip
        this up - only real code matters.
        """
        code_lines = [
            line.split("#", 1)[0]
            for cell in notebook.cells
            if cell.cell_type == "code"
            for line in cell.source.splitlines()
        ]
        code = "\n".join(code_lines)
        assert 'matplotlib.use("Agg")' in code
        assert "TkAgg" not in code
        assert "tkinter" not in code
        assert "src.gui" not in code


class TestAnnotationsAreSelfContained:
    """Guard the two silent failure modes found on 2026-07-26.

    Both produce a notebook that still runs perfectly and still looks right in
    the source, but that MMODA renders with missing labels, missing limits and
    missing provenance. Neither raises anything, so only a test catches them.
    """

    def test_no_wrapped_annotation_comments(self, notebook):
        """Each annotation must sit on the same line as its assignment.

        nb2workflow only attaches the comment on a statement's last line; a
        continuation comment silently becomes a notebook-level annotation.
        """
        source = cell_with_tag(notebook, "parameters").source
        for lineno, line in enumerate(source.splitlines(), start=1):
            stripped = line.strip()
            if not stripped.startswith("#"):
                continue
            # Only the notebook-level annotations may stand on their own line.
            assert stripped.startswith(("# oda:version", "# oda:reference")), (
                f"line {lineno} of the parameters cell is a standalone comment: "
                f"{stripped!r}. Annotations must be on the same line as their "
                "assignment, or nb2workflow will attach them to the notebook "
                "instead of the parameter."
            )

    def test_reference_is_not_a_url(self, notebook):
        """`oda:reference` must be a bare DOI.

        nb2workflow wraps anything beginning with `http` in angle brackets and
        eats the closing quote, so a URL-valued reference is dropped entirely.
        """
        source = cell_with_tag(notebook, "parameters").source
        reference = next(
            ln for ln in source.splitlines() if ln.strip().startswith("# oda:reference")
        )
        assert "http" not in reference, (
            f"{reference!r} starts with a URL scheme; nb2workflow cannot parse "
            "it. Use a bare DOI such as \"10.1051/0004-6361/202037850\"."
        )


class TestNb2WorkflowIntrospection:
    """Parse the notebook with nb2workflow itself - the tool MMODA runs."""

    @pytest.fixture(scope="class")
    def adapter(self):
        pytest.importorskip("nb2workflow")
        from nb2workflow.nbadapter import NotebookAdapter

        return NotebookAdapter(str(NOTEBOOK))

    def test_all_parameters_are_discovered(self, adapter):
        assert set(adapter.extract_parameters()) == EXPECTED_PARAMETERS

    def test_every_parameter_keeps_its_label(self, adapter):
        """A lost label means the web form shows a raw variable name."""
        for name, detail in adapter.extract_parameters().items():
            assert "oda:label" in (detail.get("extra_ttl") or ""), (
                f"{name} reached nb2workflow without its label"
            )

    def test_radius_keeps_both_limits(self, adapter):
        """The upper limit is what stops a user asking for a 5000 degree cone."""
        ttl = adapter.extract_parameters()["radius"]["extra_ttl"]
        assert "oda:lower_limit" in ttl
        assert "oda:upper_limit" in ttl

    def test_selection_parameters_keep_their_group(self, adapter):
        parameters = adapter.extract_parameters()
        for name in ("snr_threshold", "dm_min", "dm_max"):
            assert "oda:group" in parameters[name]["extra_ttl"]

    def test_outputs_carry_the_expected_owl_types(self, adapter):
        declared = adapter.extract_output_declarations()
        assert set(declared) == set(EXPECTED_OUTPUTS)
        for name, owl_type in EXPECTED_OUTPUTS.items():
            assert declared[name]["owl_type"].endswith(owl_type)

    def test_notebook_level_annotations_survive(self, adapter):
        ttl = adapter.extra_ttl
        assert "oda:version" in ttl
        assert "oda:reference" in ttl, (
            "oda:reference was dropped - it is almost certainly written as a URL"
        )

    def test_nothing_leaked_to_the_notebook_level(self, adapter):
        """Only version and reference belong on the notebook itself.

        A stray oda:label or oda:description here means some parameter's
        annotation was wrapped onto a continuation line and got reassigned.
        """
        ttl = adapter.extra_ttl
        for leaked in ("oda:label", "oda:description", "oda:group", "oda:upper_limit"):
            assert leaked not in ttl, (
                f"{leaked} leaked to the notebook level; a parameter annotation "
                "is wrapped onto a second line"
            )


@pytest.mark.slow
class TestNotebookExecution:
    """Run the notebook the way MMODA does, from an unrelated directory."""

    def run(self, tmp_path, **parameters):
        papermill = pytest.importorskip("papermill")
        output = tmp_path / "executed.ipynb"
        papermill.execute_notebook(
            str(NOTEBOOK),
            str(output),
            parameters=parameters,
            kernel_name="python3",
            cwd=str(tmp_path),
            progress_bar=False,
        )
        executed = nbformat.read(str(output), as_version=4)
        text = "\n".join(
            o["text"]
            for c in executed.cells
            for o in c.get("outputs", [])
            if o.get("output_type") == "stream"
        )
        return tmp_path, text

    def test_whole_sky_run_produces_both_images(self, tmp_path):
        workdir, text = self.run(tmp_path, radius=180.0, snr_threshold=8.0)
        assert "380 of 380 transients match" in text
        assert (workdir / "utr2_sky_map.png").stat().st_size > 0
        assert (workdir / "utr2_histograms.png").stat().st_size > 0

    def test_cone_search_narrows_the_selection(self, tmp_path):
        _workdir, text = self.run(
            tmp_path,
            src_name="Cas A",
            RA=350.85,
            DEC=58.815,
            radius=20.0,
            snr_threshold=8.0,
        )
        assert "10 of 380 transients match" in text
        assert "within 20 deg" in text

    def test_impossible_query_fails_with_an_explanation(self, tmp_path):
        papermill = pytest.importorskip("papermill")
        with pytest.raises(papermill.PapermillExecutionError) as excinfo:
            self.run(tmp_path, radius=180.0, snr_threshold=10_000.0)
        assert "No transients" in str(excinfo.value)
