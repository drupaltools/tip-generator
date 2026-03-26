# Publishing tip-generator to PyPI

## Prerequisites

- Python 3.11+
- PyPI account with API token
- Git repository with push access

## Setup

### 1. Install build tools

```bash
pip install --upgrade build twine
```

### 2. Configure PyPI credentials

Create `~/.pypirc`:

```ini
[pypi]
username = __token__
password = pypi-...
```

Or use environment variable:

```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-...
```

## Build

```bash
# Clean previous builds
rm -rf dist/ build/ src/*.egg-info

# Build package
python -m build
```

Output:
- `dist/tip_generator-X.X.X-py3-none-any.whl`
- `dist/tip_generator-X.X.X.tar.gz`

## Publish

### Manual publish

```bash
# Check package before upload
twine check dist/*

# Upload to PyPI
twine upload dist/*
```

### Automated publish via GitHub Actions

The workflow `.github/workflows/publish.yml` automatically publishes on tag push:

```bash
# Update version in pyproject.toml first
# Then create and push tag
git tag v0.1.0
git push origin v0.1.0
```

## Version Bumping

1. Update `version` in `pyproject.toml`
2. Update `__version__` in `src/tip_generator/__init__.py`
3. Commit changes
4. Create tag matching version

```bash
# Example: bump to 0.2.0
sed -i 's/version = "0.1.0"/version = "0.2.0"/' pyproject.toml
sed -i 's/__version__ = "0.1.0"/__version__ = "0.2.0"/' src/tip_generator/__init__.py
git commit -am "Bump version to 0.2.0"
git tag v0.2.0
git push origin master --tags
```

## Test Publishing (TestPyPI)

```bash
# Build
python -m build

# Upload to TestPyPI first
twine upload --repository testpypi dist/*

# Test install
pip install --index-url https://test.pypi.org/simple/ tip-generator
```

## Verify Installation

```bash
pipx install drupaltools-tip-generator
drupaltools-tip-generator --help
```
