#!/usr/bin/env python3
"""Build the MMODA service container on your own machine.

This reproduces *exactly* the Docker image that MMODA's build bot creates from
this repository, so you can run and test the web service locally before it is
ever deployed. It does three things:

  1. exports a clean snapshot of the last commit (``git archive HEAD``), which is
     byte-for-byte what MMODA clones — no ``.venv`` or ``.git`` sneaks in;
  2. renders the real MMODA ``Dockerfile`` from ``nb2workflow``'s own template,
     honouring ``mmoda.yaml`` (the notebook lives in ``mmoda/``, pattern
     ``utr2_.*``, base image ``mambaorg/micromamba``);
  3. optionally runs ``docker build`` on that context.

It intentionally does **not** need the heavyweight deploy machinery
(``kubernetes``, a container registry, a running k8s cluster). All it needs is
``git``, a working Docker, and ``nb2workflow`` importable in the current
environment.

Prerequisites
-------------
* Docker installed and running (Docker Desktop on Windows/macOS).
* A virtual environment with the service dependencies::

      python -m venv .venv
      .venv\\Scripts\\Activate.ps1        # Windows PowerShell
      # source .venv/bin/activate         # macOS / Linux
      pip install -r requirements.txt nb2workflow

* All your changes committed — the build uses the last commit, not the working
  tree. Commit first if you edited the notebook.

Usage
-----
Run from the repository root::

    python mmoda/build_local_image.py --build

That writes the image as ``nb-utr2:local`` by default. Then start and query it::

    docker run -d --name utr2svc -p 8000:8000 nb-utr2:local
    curl "http://localhost:8000/api/v1.0/get/utr2_transients?radius=180"

Pass ``--tag`` to change the image name, or omit ``--build`` to only generate
the build context and print its path (useful for inspecting the Dockerfile).
"""

from __future__ import annotations

import argparse
import io
import re
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

import yaml
from jinja2 import Environment, PackageLoader
from nb2workflow import version

# nb2workflow.deploy uses this same default when a repo pins no Python version.
DEFAULT_PYTHON_VERSION = "3.10"


def repo_root() -> Path:
    """Absolute path of the git repository this script lives in."""
    out = subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=Path(__file__).resolve().parent,
    )
    return Path(out.decode().strip())


def render_dockerfile(repo: Path) -> str:
    """Render the exact Dockerfile MMODA's nb2workflow deploy step generates.

    Mirrors ``nb2workflow.deploy.NBRepo.generate_dockerfile`` so the result
    tracks whatever version of nb2workflow is installed.
    """
    # mmoda.yaml tells MMODA the notebook is under mmoda/ and matches utr2_.*
    config = {"notebook_path": "", "filename_pattern": ".*", "use_repo_base_image": False}
    mmoda_yaml = repo / "mmoda.yaml"
    if mmoda_yaml.exists():
        config.update(yaml.safe_load(mmoda_yaml.read_text()) or {})

    # A conda environment.yml with a pinned python keeps that pin; otherwise
    # nb2workflow injects DEFAULT_PYTHON_VERSION with yq at build time.
    has_conda_env = False
    inject_python_version_str = (
        f"/tmp/yq -i '.dependencies += \"python={DEFAULT_PYTHON_VERSION}\"' "
        "/repo/environment.yml"
    )
    env_file = repo / "environment.yml"
    if env_file.exists():
        dependencies = (yaml.safe_load(env_file.read_text()) or {}).get("dependencies")
        if dependencies is not None:
            has_conda_env = True
            pinned = re.compile(r"^python[~=<> ]")
            for dep in dependencies:
                if isinstance(dep, str) and pinned.match(dep):
                    inject_python_version_str = f'echo "Using {dep}"'
                    break

    def git(*args: str) -> str:
        return subprocess.check_output(["git", *args], cwd=repo).decode().strip()

    metadata = {
        "descr": git("describe", "--always", "--tags"),
        "author": git("log", "-1", "--pretty=format:%an <%ae>"),
        "last_change_time": git("log", "-1", "--pretty=format:%ai"),
    }

    nb2wversion = version(print_it=False)
    jenv = Environment(loader=PackageLoader("nb2workflow"))
    template = jenv.get_template("Dockerfile.jinja")
    return template.render(
        dockerfile_base=None,
        source_from="localdir",
        git_origin="local",
        has_conda_env=has_conda_env,
        inject_python_version_str=inject_python_version_str,
        default_python_version=DEFAULT_PYTHON_VERSION,
        nb2w_version_spec=f"nb2workflow[service]=={nb2wversion}",
        metadata=metadata,
        nbpath="/repo/" + config["notebook_path"].strip("/"),
        filename_pattern=config["filename_pattern"],
    )


def make_build_context(repo: Path, dest: Path) -> None:
    """Populate *dest* with nb-repo/ (a clean HEAD snapshot) and a Dockerfile."""
    nb_repo = dest / "nb-repo"
    nb_repo.mkdir(parents=True, exist_ok=True)
    archive = subprocess.check_output(["git", "archive", "HEAD"], cwd=repo)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(nb_repo)  # tracked files only: no .venv, no .git
    # newline="\n": the Dockerfile must use LF even when generated on Windows.
    with open(dest / "Dockerfile", "w", encoding="utf-8", newline="\n") as handle:
        handle.write(render_dockerfile(repo))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--build", action="store_true", help="run `docker build` on the generated context")
    parser.add_argument("--tag", default="nb-utr2:local", help="image tag to build (default: nb-utr2:local)")
    parser.add_argument(
        "--context",
        type=Path,
        default=None,
        help="directory for the build context (default: a fresh temp directory)",
    )
    args = parser.parse_args(argv)

    repo = repo_root()
    context = args.context or Path(tempfile.mkdtemp(prefix="utr2-mmoda-build-"))
    context.mkdir(parents=True, exist_ok=True)

    make_build_context(repo, context)
    print(f"Build context ready at: {context}")
    print(f"Dockerfile:             {context / 'Dockerfile'}")

    if not args.build:
        print("\nInspect the Dockerfile above, or build it yourself with:")
        print(f'    docker build "{context}" -t {args.tag}')
        return 0

    print(f"\nBuilding image {args.tag} (this can take several minutes the first time)...\n")
    result = subprocess.run(["docker", "build", str(context), "-t", args.tag])
    if result.returncode != 0:
        print("\nBuild failed. See the Docker output above.", file=sys.stderr)
        return result.returncode

    print(f"\nBuilt {args.tag}. Start and test the service with:")
    print(f"    docker run -d --name utr2svc -p 8000:8000 {args.tag}")
    print('    curl "http://localhost:8000/api/v1.0/get/utr2_transients?radius=180"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
