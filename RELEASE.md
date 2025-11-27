# Release Process

PyIV uses automatic semantic versioning and release generation based on commit messages and successful CI builds.

## How It Works

1. **Automatic Triggering**: When code is pushed to `main` and CI passes successfully, the release workflow automatically:
   - Analyzes commit messages since the last release
   - Determines the appropriate version bump (major/minor/patch)
   - Updates the version in `pyproject.toml`
   - Builds source distribution (tarball) and wheel
   - Creates a Git tag
   - Creates a GitHub Release with the distribution files

2. **Version Bump Logic**:
   - **Major** (x.0.0): Breaking changes, major features, or commits with "breaking", "major", or "!" in the message
   - **Minor** (0.x.0): New features, additions, or commits with "feat", "feature", "add", or "new" in the message
   - **Patch** (0.0.x): Bug fixes, documentation, or other changes

## Manual Release

You can also trigger a release manually:

1. Go to **Actions** → **Release** workflow
2. Click **Run workflow**
3. Choose version bump type:
   - **auto**: Automatically determine from commit messages (default)
   - **major**: Bump major version
   - **minor**: Bump minor version
   - **patch**: Bump patch version

## Commit Message Guidelines

For best automatic version detection, use conventional commit messages:

- `feat: add new feature` → Minor version bump
- `fix: fix bug` → Patch version bump
- `BREAKING: change API` → Major version bump
- `feat!: breaking change` → Major version bump

## Distribution Files

Each release includes:
- **Source Distribution** (`.tar.gz`): Contains the source code
- **Wheel Distribution** (`.whl`): Pre-built binary distribution

Both are automatically attached to the GitHub Release and can be installed via:
```bash
pip install pyiv==<version>
```

## Release Artifacts

Release artifacts are:
- Uploaded to GitHub Releases
- Available for 30 days as workflow artifacts
- Automatically tagged with `v<version>` format

