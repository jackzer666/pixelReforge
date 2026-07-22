# PixelReforge Pipeline

[简体中文](README.md) | [English](README.en.md)

> **PixelReforge**  
> A batch pipeline for restoring clean, grid-aligned pixel art.

PixelReforge is a command-line pipeline for refining pixel art and organizing batch-processing results. Built on [perfect-pixel](https://github.com/theamusing/perfectPixel), it detects and reconstructs pixel grids while providing content-based deduplication, persistent state tracking, failure isolation, and source-file archiving.

## Features

- Supports PNG, JPG, JPEG, WEBP, and BMP images;
- Processes entire directories, individual files, or nested directory trees;
- Produces both a native-resolution pixel image and a nearest-neighbor enlarged preview;
- Identifies duplicate tasks from image content and processing parameters;
- Archives successful and failed inputs separately without allowing one failure to interrupt the batch;
- Persists processing state as JSON and prints clear progress and summary messages;
- Uses a project-local virtual environment and lockfile for dependency isolation and reproducible setup.

## Requirements

- Python 3.10 or later;
- [uv](https://docs.astral.sh/uv/);
- macOS, Linux, or Windows.

## Quick Start

### 1. Install the project dependencies

From the project root, create the project environment from the lockfile:

```bash
uv sync --locked
```

This command creates `.venv/` in the project root and installs the locked dependencies together with the current project. The environment belongs exclusively to this project and does not modify the global Python installation.

You normally do not need to activate the virtual environment because subsequent commands can be run through `uv run`. To activate it manually, use the command for your platform:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

### 2. Prepare the input images

Place the images to be processed in the `input/` directory at the project root:

```text
input/
├── character.png
└── landscape.webp
```

Required runtime directories are created automatically if they do not already exist.

### 3. Start batch processing

```bash
uv run pixel-reforge
```

PixelReforge scans `input/` for supported images and processes each file through grid detection, pixel-art reconstruction, state recording, and source archiving.

### 4. Review the results

- Generated images are written to `output/`;
- Successfully processed or duplicate source files are moved to `processed/`;
- Failed source files are moved to `failed/`;
- Task state is stored in `data/process_state.json`.

## Usage

### Process a specific directory

```bash
uv run pixel-reforge --input-dir ~/Pictures/pixel-input
```

### Process a single image

```bash
uv run pixel-reforge --file ~/Pictures/character.png
```

If the image is inside `input/` under the current working directory, it is archived according to the result. If it is outside `input/`, PixelReforge generates the output without moving the source file.

### Select a custom output directory

```bash
uv run pixel-reforge \
  --input-dir ~/Pictures/pixel-input \
  --output-dir ~/Pictures/pixel-output
```

### Scan nested directories

```bash
uv run pixel-reforge --recursive
```

Recursive mode scans all subdirectories under the selected input directory. If that directory contains project-managed directories, PixelReforge automatically excludes `output/`, `processed/`, `failed/`, and `data/` to prevent generated files from being processed again.

### Retry failed tasks

```bash
uv run pixel-reforge --retry-failed
```

This command reads images from `failed/`. Successfully retried files are moved to `processed/`, while files that fail again remain in `failed/`.

### Force reprocessing

```bash
uv run pixel-reforge --force
```

The `--force` option ignores existing successful records and regenerates the outputs.

## Command-Line Options

| Option | Description | Default |
| --- | --- | --- |
| `--file PATH` | Process one specific image | None |
| `--input-dir PATH` | Process images from a specific directory | `input/` |
| `--output-dir PATH` | Write generated images to a specific directory | `output/` |
| `--retry-failed` | Retry images stored in `failed/` | Disabled |
| `--scale INTEGER` | Set the preview scale factor; minimum value is 2 | `8` |
| `--force` | Ignore existing successful records and process again | Disabled |
| `--recursive` | Recursively scan input subdirectories | Disabled |
| `-h`, `--help` | Display command help | — |

`--file`, `--input-dir`, and `--retry-failed` are mutually exclusive input modes. Only one may be selected for each invocation.

## Processing Workflow

Each image passes through the following steps:

1. Read the image and calculate its SHA-256 content fingerprint;
2. Combine the fingerprint, algorithm version, and processing parameters into a task identifier;
3. Check whether a complete successful result already exists;
4. Use `perfect-pixel` to detect the grid and reconstruct clean pixel art;
5. Generate a native-resolution result and a nearest-neighbor enlarged preview;
6. Atomically write the output files and JSON state record;
7. Archive or isolate the source file according to the result.

An existing result is reused only when the task identifier matches, its state is successful, and both output files still exist. A change to the processing parameters or core dependency version causes the same input image to be treated as a new task.

## Output Files

Each successfully processed image produces two PNG files:

```text
source_YYYYMMDD_HHMMSS_microseconds_1x.png
source_YYYYMMDD_HHMMSS_microseconds_8x.png
```

- The `1x` file contains the reconstructed image at its native pixel-grid resolution;
- The `8x` file is an eight-times enlarged preview by default; the actual factor is controlled by `--scale`;
- If a filename collision occurs, a sequence number is appended automatically instead of overwriting an existing file;
- Both outputs are first written to temporary files and published only after they have been generated successfully.

## Project Layout

```text
pixel_reforge/             Python source package
tests/                     Automated tests
input/                     Default input directory
output/                    Generated output directory
processed/                 Archive for successful or duplicate sources
failed/                    Isolation directory for failed sources
data/process_state.json    Persistent processing state
pyproject.toml             Project metadata and direct dependencies
uv.lock                    Complete dependency lockfile
```

The state file stores only source fingerprints, processing parameters, task states, error messages, and output paths. It does not contain image data.

## Exit Status

- The command exits with `0` when every task succeeds or matches an existing result;
- The command exits with `1` when any image fails or the application encounters a fatal error.

PixelReforge can therefore be integrated directly into shell scripts, scheduled jobs, and other automated pipelines.

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

Synchronize the environment strictly from the existing lockfile:

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
