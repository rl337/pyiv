# Release Process

pyiv versions live in `pyproject.toml` and `pyiv/__init__.py`. Patch/minor
bumps on `main` are automatic. **Major versions** (and the first PyPI
release, 0.3.0) are set by hand.

## Automatic patch/minor

After CI succeeds on `main`, **Auto Version Bump** increments:

- **Patch** on a regular (including squash) commit
- **Minor** on a merge commit

It does **not** bump when:

- The commit message contains `[skip bump]`
- `pyproject.toml` is already newer than the latest git tag (a manual major)

Those bump commits use `[skip ci]` so they do not loop.

## GitHub Release

The **Release** workflow reads the version already in `pyproject.toml`. It
does not bump. If `vX.Y.Z` is missing, it tags that version, attaches
sdist/wheel, and opens a GitHub Release.

Install line for every production release:

```bash
pip install pyiv==<version>
```

User-facing notes live in `CHANGELOG.md`. Put new bullets under **Unreleased**
in the same PR; after the auto-bump, move them to `## X.Y.Z`. GitHub Release
bodies should match those bullets.

## Publish to TestPyPI / PyPI

PyPI gets **only** final `X.Y.Z` builds. No RCs, nightlies, or `--pre`.
TestPyPI is a pipeline smoke test, not a user channel.

Trusted Publishing (OIDC) — no API tokens in GitHub secrets:

1. On [TestPyPI publishing](https://test.pypi.org/manage/account/publishing/)
   and [PyPI publishing](https://pypi.org/manage/account/publishing/), add a
   pending publisher: owner `rl337`, repo `pyiv`, workflow `release.yml`,
   environment left blank. Repeat for project **`pyiv-common`** (same
   repo/workflow). `pyiv-common` versions independently (starts at 0.1.0)
   and is not auto-bumped with core.
2. After `0.3.0` is on `main`, **Actions → Release → Run workflow**:
   - First: **publish_target = testpypi**. Confirm
     `pip install -i https://test.pypi.org/simple/ --no-deps pyiv==0.3.0`.
   - Then: **publish_target = pypi**.

Re-running TestPyPI for the same version is allowed (`skip-existing`).
Production PyPI versions are immutable. The release workflow also builds
`pyiv-common`; `skip-existing` lets a core-only bump skip a
`pyiv-common` version that is already on the index.

## Manual GitHub Release only

**Actions → Release → Run workflow** with **publish_target = none** tags and
attaches artifacts without uploading to either index.
