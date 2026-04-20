# Deploy GitHub Pages

## Deployment target

The Pages deployment publishes the static `web/` directory. No server runtime is
required after assets are staged.

## Workflow

The deployment workflow is `.github/workflows/pages.yml`.

On `main` or manual dispatch it:
1. checks out the repository,
2. installs `uv`,
3. uses `.python-version`,
4. runs `uv sync --locked --dev`,
5. runs `make stage-web`,
6. uploads `web/` as the Pages artifact,
7. deploys with `actions/deploy-pages`.

## Local preflight

```bash
uv sync --dev
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
