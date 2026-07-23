# PixelReforge Pipeline

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-STDIO-6A5ACD.svg)](docs/mcp.en.md)
[![uv](https://img.shields.io/badge/package%20manager-uv-DE5FE9.svg)](https://docs.astral.sh/uv/)

[简体中文](README.md) | [English](README.en.md)

> A CLI and MCP pipeline for refining and reconstructing AI-generated pixel art.

PixelReforge refines, reconstructs, and archives AI-generated pixel art. Built on [perfect-pixel](https://github.com/theamusing/perfectPixel), it detects and reconstructs logical pixel grids through both a command-line interface and a local STDIO MCP integration for Codex and other compatible clients.

## Why PixelReforge

An AI-generated image may look like pixel art while still containing:

- Inconsistent logical pixel sizes or shifted grid boundaries;
- Blurred edges and near-duplicate colors caused by antialiasing, interpolation, or compression;
- Output dimensions that do not match the intended logical pixel grid;
- Batch assets without consistent deduplication, state tracking, or archiving.

PixelReforge can redetect the grid and resample each cell, producing a clean `1x` pixel image and a nearest-neighbor enlarged preview for further editing, review, and delivery.

## Features

- Supports PNG, JPG, JPEG, WEBP, and BMP;
- Processes individual images, directories, and nested directory trees;
- Provides `detect` automatic grid detection and `source` native-pixel modes;
- Produces both a `1x` pixel image and nearest-neighbor enlarged preview;
- Deduplicates tasks by image content, algorithm version, and parameters;
- Persists task state and archives successful and failed sources separately;
- Exposes a local STDIO MCP server with the `reforge_image` tool.

## Quick Start

Requirements: Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
# Install locked dependencies
uv sync --locked

# Place images in input/, then start the batch
uv run pixel-reforge
```

Processing results:

- `output/`: `1x` results and enlarged previews;
- `processed/`: successful or previously processed sources;
- `failed/`: failed sources;
- `data/process_state.json`: persistent task state.

See the [CLI guide](docs/cli.en.md) for commands, options, and output conventions.

## Pixel Modes

| Mode | Behavior | Intended use |
| --- | --- | --- |
| `detect` | Detect the logical grid and resample each cell | AI-generated, enlarged, slightly blurred, or irregular pixel art |
| `source` | Treat every input pixel as one `1×1` logical pixel | Images already produced at native pixel dimensions |

```bash
uv run pixel-reforge --pixel-mode detect
uv run pixel-reforge --pixel-mode source
```

## MCP Quick Entry

Start the local STDIO MCP server:

```bash
PIXEL_REFORGE_ROOT=/path/to/pixelReforge uv run pixel-reforge-mcp
```

The server exposes the `reforge_image` write tool, allowing Codex and other clients to process images in `input/` and receive actual task status and output paths.

For complete arguments, global Codex configuration, and an AI-generation-to-reforging prompt, see the [MCP and Codex integration guide](docs/mcp.en.md).

## Documentation

| Document | Contents |
| --- | --- |
| [CLI guide](docs/cli.en.md) | Installation, common commands, complete options, processing, and outputs |
| [MCP and Codex integration](docs/mcp.en.md) | MCP tool arguments, Codex configuration, and invocation examples |
| [Development guide](docs/development.en.md) | Project layout, testing, and dependency management |
