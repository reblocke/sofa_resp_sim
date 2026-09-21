# Deploy GitHub Pages

## Deployment target

The Pages deployment publishes the static `web/` directory. No server runtime is
required after assets are staged.

## Workflow

The deployment workflow is `.github/workflows/pages.yml`.

On `main` or manual dispatch it first calls the local reusable CI workflow for
that same commit. The Pages build requires successful checks before it can run;
deployment requires the successful build. The called CI workflow verifies
formatting, lint, the frozen catalogue, native/scientific tests, real Chromium
browser behavior and native/Pyodide parity, then builds and checks exact
reproduction in a fresh locked wheel installation. Test receipts are uploaded
as a commit-named Actions artifact, including on failure.

After those checks pass, the build checks out the same workflow commit, installs
`uv` and the Python version from `.python-version`, synchronizes the locked dev
environment, stages the web assets and uploads `web/` as the Pages artifact.
The deploy job publishes that artifact with `actions/deploy-pages`.

Local checks do not establish a successful remote run. Record the Actions run
and tested commit when satisfying the integration gate. A Pages workflow change
does not itself authorize or demonstrate publication.

## Local preflight

```bash
uv sync --locked --dev
make verify
uv run python -m build
```

If browser dependencies are missing locally, install Chromium once:

```bash
uv run playwright install chromium
```

## Generated assets

Do not commit:
- `web/assets/py/`
- `web/assets/data/`

They are regenerated in CI by `make stage-web`.

## Repository settings

GitHub Pages must be configured to deploy from GitHub Actions. The workflow
needs Pages permissions:
- `contents: read`
- `pages: write`
- `id-token: write`
