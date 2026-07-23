# PixelReforge CLI Guide

[中文](cli.md) | [Back to English README](../README.en.md)

This guide covers installation, command-line options, processing behavior, and output conventions.

## Requirements

- Python 3.10 or later;
- [uv](https://docs.astral.sh/uv/);
- macOS, Linux, or Windows.

## Installation

Create the project environment from the lockfile:

```bash
uv sync --locked
```

This creates a project-local `.venv/` and installs the locked dependencies. Manual activation is normally unnecessary because commands can be run through `uv run`.

To activate the environment manually:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

## Quick Start

Place images in the project-level `input/` directory:

```text
input/
├── character.png
└── landscape.webp
```

Start the default batch:

```bash
uv run pixel-reforge
```

Required runtime directories are created automatically. After processing:

- Generated images are written to `output/`;
- Successful or duplicate sources are moved to `processed/`;
- Failed sources are moved to `failed/`;
- Task state is stored in `data/process_state.json`.

## Common Commands

Process a specific directory:

```bash
uv run pixel-reforge --input-dir ~/Pictures/pixel-input
```

Process one image:

```bash
uv run pixel-reforge --file ~/Pictures/character.png
```

An image inside the current project's `input/` directory is archived according to the result. An image outside `input/` is processed without moving the source.

Select a custom output directory:

```bash
uv run pixel-reforge \
  --input-dir ~/Pictures/pixel-input \
  --output-dir ~/Pictures/pixel-output
```

Scan nested directories:

```bash
uv run pixel-reforge --recursive
```

Recursive mode excludes `output/`, `processed/`, `failed/`, and `data/` to prevent generated files from being processed again.

Retry tasks from `failed/`:

```bash
uv run pixel-reforge --retry-failed
```

Ignore successful records and regenerate outputs:

```bash
uv run pixel-reforge --force
```

## Command-Line Options

| Option | Description | Default |
| --- | --- | --- |
| `--file PATH` | Process one specific image | None |
| `--input-dir PATH` | Process images from a specific directory | `input/` |
| `--output-dir PATH` | Write generated images to a specific directory | `output/` |
| `--retry-failed` | Retry images stored in `failed/` | Disabled |
| `--scale INTEGER` | Set the preview scale factor; minimum value is 2 | `8` |
| `--pixel-mode {detect,source}` | Detect the logical grid or treat every input pixel as `1×1` | `detect` |
| `--force` | Ignore successful records and process again | Disabled |
| `--recursive` | Recursively scan input subdirectories | Disabled |
| `-h`, `--help` | Display command help | — |

`--file`, `--input-dir`, and `--retry-failed` are mutually exclusive input modes.

### Pixel Modes

- `detect`: use `perfect-pixel` to detect and reconstruct the logical grid; intended for images that look like pixel art but have irregular grids or cell colors;
- `source`: skip grid detection and treat each input pixel as one `1×1` logical pixel; intended for images already produced at native pixel dimensions.

In `source` mode, the `1x` output matches the input dimensions and each preview dimension is multiplied by `--scale`.

## Processing Workflow

Each image passes through these steps:

1. Read the image and calculate its SHA-256 content fingerprint;
2. Combine the fingerprint, algorithm version, and parameters into a task identifier;
3. Check for an existing complete successful result;
4. Reconstruct or directly use the pixel image according to the selected mode;
5. Generate a `1x` result and nearest-neighbor enlarged preview;
6. Atomically write output files and the JSON state record;
7. Archive or isolate the source according to the result.

An existing result is reused only when the task identifier matches, its state is successful, and both output files exist. Parameter or core dependency version changes make the same input a new task.

## Output Files

Each successful image produces two PNG files:

```text
source_YYYYMMDD_HHMMSS_microseconds_1x.png
source_YYYYMMDD_HHMMSS_microseconds_8x.png
```

- The `1x` file contains the reconstructed or directly used logical pixel image;
- The `8x` file is an eight-times preview by default; `--scale` controls the actual factor;
- Filename collisions receive a sequence number instead of overwriting an existing file;
- Both outputs are written to temporary files and published only after both succeed.

## Runtime Directories

```text
input/                     Default input directory
output/                    Generated output directory
processed/                 Archive for successful or duplicate sources
failed/                    Isolation directory for failed sources
data/process_state.json    Persistent processing state
```

The state file stores fingerprints, parameters, task states, errors, and output paths, but no image data.

## Exit Status

- Returns `0` when every task succeeds or matches an existing result;
- Returns `1` when any image fails or the application encounters a fatal error.

PixelReforge can therefore be integrated into shell scripts, scheduled jobs, and other automated pipelines.
