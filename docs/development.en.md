# PixelReforge Development Guide

[中文](development.md) | [Back to English README](../README.en.md)

## Project Layout

```text
pixel_reforge/             Python source package
pixel_reforge/mcp_adapter/ MCP STDIO adapter
tests/                     Automated tests
pyproject.toml             Project metadata and direct dependencies
uv.lock                    Complete dependency lockfile
```

## Testing

Run the complete test suite from the project root:

```bash
uv run python -m unittest discover -s tests -v
```

## Dependency Management

Direct dependencies are declared in `pyproject.toml`. Exact resolved versions and file checksums are recorded in `uv.lock`. Commit `uv.lock` with project changes, but do not commit `.venv/` or `*.egg-info/`.

Add a dependency:

```bash
uv add PACKAGE_NAME
```

Remove a dependency:

```bash
uv remove PACKAGE_NAME
```

Synchronize strictly from the existing lockfile:

```bash
uv sync --locked
```

Upgrade dependencies and update the lockfile:

```bash
uv lock --upgrade
uv sync
```

## Core Dependencies

- [perfect-pixel](https://github.com/theamusing/perfectPixel): detects and refines pixel grids;
- [OpenCV](https://opencv.org/): reads images, converts color spaces, scales results, and writes output files.
