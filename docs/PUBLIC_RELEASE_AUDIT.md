# Public release audit

## Current status

Last local audit: 2026-06-26.

No PHI, patient identifiers, patient-level extracts, credentials, tokens, SSNs,
MRNs, DOBs, emails, phone numbers, or obvious confidential research data were
found in the tracked `main` tree during the local scan.

The current tracked tree is intended to contain:
- source code,
- tests,
- documentation,
- static web app source,
- small synthetic or aggregate validation artifacts.

## History rewrite status

On 2026-06-26, branch history was rewritten with `git-filter-repo` to remove
two publisher-controlled literature PDFs from all writable branch refs:
- `docs/approaches_to_converting_spo2_fio2_ratio_to.18.pdf`
- `docs/ccm_54_4_2025_12_09_chaudhuri_ccmed-d-25-00833_sdc1 (1).pdf`

The forced mirror push updated `main` from `bcc0b7a` to rewritten commit
`ee81c8c` and deleted stale non-main branches from `origin`. A fresh mirror clone
confirmed that `refs/heads/main` no longer contains the PDF paths or blob hashes.

## Known remaining public-exposure blocker

GitHub rejected updates to read-only hidden PR refs during the mirror push. A
fresh mirror clone still finds the two PDF blob hashes through GitHub PR refs:
- `fa1ac7169009ecdc21dacaf58b1243385aee2f79`
- `dec85ea60ab065fd7e54340a39cd2c2a5fd85880`

`git-filter-repo` reported first changed commit
`e7b4b32596cb01c5f71e725d14f840b7afba99d6` and affected PR refs:
- `refs/pull/3/head`
- `refs/pull/4/head`
- `refs/pull/5/head`
- `refs/pull/6/head`
- `refs/pull/7/head`
- `refs/pull/8/head`

The PDFs did not appear to contain PHI in the local text/metadata inspection,
but they are publisher-controlled documents and should not be redistributed
through repository history without confirming rights.

To fully resolve public exposure on the existing hosted repository, request
GitHub Support dereference/delete the affected PR refs, run repository garbage
collection, and clear cached views. If GitHub Support declines because this is
rights/provenance cleanup rather than PHI or credential exposure, publish a
fresh public repository from a clean `HEAD` export and make this repository
private or archived.

## Suggested audit commands

Run from repo root:

```bash
git status --short --branch --ignored=matching
git ls-files
git log --all --name-only --pretty=format: | sort -u
git rev-list --objects --all | rg -i '(patient|phi|mrn|dob|ssn|secret|token|key|\\.pdf$|\\.csv$|\\.xlsx$|\\.parquet$|\\.dta$)'
git grep -n -I -E '(MRN|patient[ _-]?(id|name|dob|birth|record)|DOB|SSN|token|secret|password|api[_-]?key|private key)' -- ':!uv.lock'
```

If available, also run a dedicated secret scanner such as `gitleaks` or
`trufflehog` against all history.

## Automated regression coverage

`tests/contracts/test_public_release_hygiene.py` provides a deterministic check
for the tracked `HEAD` tree and app/browser surface. It verifies:
- no disallowed tracked file types such as PDFs, spreadsheets, databases, keys,
  or dotenv files are present at `HEAD`,
- tracked/package/staged CSV headers do not expose obvious patient or
  confidential identifiers,
- browser contract payload keys and CSV exports do not expose those identifiers,
- staged web data remains limited to the allowlisted aggregate reference CSV.

This automated check does not replace the manual all-history audit above. Old
git history, PR refs, and previously hosted blobs must still be reviewed
separately before changing repository visibility.

## Policy

- Do not commit PHI, patient-level raw extracts, restricted data, credentials,
  or publisher PDFs.
- Keep `docs/*.pdf` ignored unless a specific documented licensing/provenance
  decision says otherwise.
- Keep checked-in validation artifacts small, synthetic or aggregate, and
  documented in `artifacts/README.md`.
- Keep generated `web/assets/py/` and `web/assets/data/` outputs ignored and
  reproducible from tracked source/artifacts.
