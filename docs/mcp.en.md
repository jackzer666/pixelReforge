# PixelReforge MCP and Codex Integration

[中文](mcp.md) | [Back to English README](../README.en.md)

PixelReforge provides a local STDIO MCP server so Codex and other MCP-compatible clients can process images in `input/` directly.

## Start the MCP Server

Synchronize the environment from the project root:

```bash
uv sync --locked
```

Start the local STDIO entry point:

```bash
PIXEL_REFORGE_ROOT=/path/to/pixelReforge uv run pixel-reforge-mcp
```

## The `reforge_image` Tool

The server exposes one write tool, `reforge_image`:

| Argument | Description | Default |
| --- | --- | --- |
| `source_path` | Image path relative to the project `input/` directory | Required |
| `scale` | Preview scale factor; minimum value is 2 | `8` |
| `pixel_mode` | `detect` the grid or treat each source pixel as `1×1` with `source` | `detect` |
| `sample_method` | `center` or `majority` | `center` |
| `refine_intensity` | Grid refinement strength from 0 to 1 | `0.3` |
| `force` | Ignore an existing successful record | `false` |
| `archive_source` | Move successes to `processed/` and failures to `failed/` | `true` |

The tool accepts only relative paths inside `input/`. Outputs are written to `output/` and `data/process_state.json`. Sources are archived by default and preserved only when `archive_source=false` is explicitly requested.

Image processing runs serially in a dedicated worker process, preventing ordinary third-party output from corrupting the STDIO protocol. Cancelling a client wait does not guarantee termination of processing already in progress.

## Configure Globally in Codex

The following steps register the server in the current user's global Codex configuration. User-level configuration lives in `~/.codex/config.toml`; see the [Codex configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference#configtoml).

1. Confirm that the MCP entry point is installed:

   ```bash
   test -x .venv/bin/pixel-reforge-mcp \
     && echo "pixel-reforge-mcp is ready"
   ```

2. Replace `<project-root>` with the absolute PixelReforge project path and register the server:

   ```bash
   codex mcp add pixel_reforge \
     --env PIXEL_REFORGE_ROOT="<project-root>" \
     -- "<project-root>/.venv/bin/pixel-reforge-mcp"
   ```

   If a server with this name already exists, edit its `[mcp_servers.pixel_reforge]` entry in `~/.codex/config.toml` instead of adding it again.

3. To set a stable working directory, timeouts, and write approval behavior, merge these values into the existing tables without declaring duplicate TOML tables:

   ```toml
   [mcp_servers.pixel_reforge]
   command = "<project-root>/.venv/bin/pixel-reforge-mcp"
   cwd = "<project-root>"
   enabled = true
   startup_timeout_sec = 20
   tool_timeout_sec = 300
   enabled_tools = ["reforge_image"]
   default_tools_approval_mode = "writes"

   [mcp_servers.pixel_reforge.env]
   PIXEL_REFORGE_ROOT = "<project-root>"
   ```

4. Verify the configuration Codex loads:

   ```bash
   codex mcp get pixel_reforge --json
   codex mcp list
   ```

5. Restart Codex or open a new session to reload the MCP connection and tool schema.

## Invocation Example

Ask Codex:

```text
Use pixel_reforge to process input/character.png. You must call reforge_image
with pixel_mode set to detect and a scale of 8, then report the absolute paths
of both output files.
```

The actual MCP `source_path` must be `character.png`, without the `input/` prefix and without an absolute path. Because `archive_source=true` by default, a successful source is moved to `processed/`; pass `archive_source=false` to preserve it.

The corresponding tool arguments are:

```json
{
  "source_path": "character.png",
  "scale": 8,
  "pixel_mode": "detect",
  "sample_method": "center",
  "refine_intensity": 0.3,
  "force": false,
  "archive_source": true
}
```

## From AI Generation to Pixel Reforging

After configuration, Codex can connect image generation, local file saving, and MCP processing. Replace `<project-root>` with the absolute project path:

```text
Complete the following task directly:

1. Generate PNG pixel art with a limited palette, flat color blocks, and no
   antialiasing or blur.
2. Save the actual file to:
   <project-root>/input/codex_generated_pixel_art.png
3. Confirm the file exists, then call reforge_image from the pixel_reforge MCP
   Server. Do not use the CLI or simulate a result. Use:
   {
     "source_path": "codex_generated_pixel_art.png",
     "scale": 8,
     "pixel_mode": "detect",
     "sample_method": "center",
     "refine_intensity": 0.3,
     "force": true,
     "archive_source": true
   }
4. Read the actual status, outputs, and error returned by the tool. Report the
   absolute paths of the 1x and 8x outputs and whether the source moved to
   processed/.

Do not guess output paths from filename conventions. Report the real error if
processing fails.
```

If the current Codex interface cannot continue from image generation to an MCP call in the same turn, split the workflow into two turns: first generate and save the file in `input/`, then explicitly invoke `reforge_image` with its relative path.
