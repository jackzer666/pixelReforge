# PixelReforge MCP 与 Codex 集成

[返回中文 README](../README.md) | [English](mcp.en.md)

PixelReforge 提供本地 STDIO MCP Server，使 Codex 等兼容 MCP 的客户端可以直接处理 `input/` 中的图片。

## 启动 MCP Server

在项目根目录同步环境：

```bash
uv sync --locked
```

直接启动本地 STDIO 入口：

```bash
PIXEL_REFORGE_ROOT=/path/to/pixelReforge uv run pixel-reforge-mcp
```

## `reforge_image` 工具

MCP Server 只暴露一个写工具 `reforge_image`：

| 参数 | 说明 | 默认值 |
| --- | --- | --- |
| `source_path` | 相对于项目 `input/` 的图片路径 | 必填 |
| `scale` | 预览图放大倍数，最小值为 2 | `8` |
| `pixel_mode` | `detect` 自动检测网格；`source` 按输入像素 `1×1` 处理 | `detect` |
| `sample_method` | `center` 或 `majority` | `center` |
| `refine_intensity` | 网格修正强度，范围为 0 到 1 | `0.3` |
| `force` | 是否忽略已有成功记录 | `false` |
| `archive_source` | 成功时移入 `processed/`，失败时移入 `failed/` | `true` |

工具只接受 `input/` 内的相对路径，输出写入 `output/` 和 `data/process_state.json`。默认按结果归档原图；设置 `archive_source=false` 时保留原图。

图片处理在独立工作进程中串行执行，第三方库的普通输出不会污染 STDIO 协议。客户端取消等待不保证终止已经开始的处理。

## 全局配置到 Codex

以下步骤会注册到当前用户的 Codex 全局配置。用户级配置文件位于 `~/.codex/config.toml`；字段说明参见 [Codex 配置参考](https://learn.chatgpt.com/docs/config-file/config-reference#configtoml)。

1. 确认 MCP 命令已经安装：

   ```bash
   test -x .venv/bin/pixel-reforge-mcp \
     && echo "pixel-reforge-mcp is ready"
   ```

2. 将 `<project-root>` 替换为 PixelReforge 项目根目录的绝对路径，然后注册 Server：

   ```bash
   codex mcp add pixel_reforge \
     --env PIXEL_REFORGE_ROOT="<project-root>" \
     -- "<project-root>/.venv/bin/pixel-reforge-mcp"
   ```

   如果已经存在同名 Server，不要重复添加；编辑 `~/.codex/config.toml` 中已有的 `[mcp_servers.pixel_reforge]`。

3. 如需固定工作目录、超时和写操作审批，将以下配置合并到已有表中，不要重复声明同名 TOML 表：

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

4. 检查 Codex 读取到的配置：

   ```bash
   codex mcp get pixel_reforge --json
   codex mcp list
   ```

5. 重启 Codex 或新开会话，使 MCP 连接和工具 Schema 重新加载。

## 调用示例

可以在 Codex 中要求：

```text
使用 pixel_reforge 处理 input/character.png。必须调用 reforge_image，
pixel_mode 设为 detect，放大倍数设为 8，完成后告诉我两个输出文件的绝对路径。
```

MCP 实际收到的 `source_path` 应为 `character.png`，不能包含 `input/` 前缀，也不能使用绝对路径。默认 `archive_source=true`，成功后原图会移动到 `processed/`；需要保留时应显式传入 `archive_source=false`。

对应的工具参数：

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

## 从 AI 生成到像素重铸

配置完成后，可以让 Codex 串联图片生成、文件保存和 MCP 处理。将 `<project-root>` 替换为项目根目录的绝对路径：

```text
请直接完成下面的任务：

1. 生成一张有限色板、平涂色块、无抗锯齿和模糊的 PNG 像素画。
2. 将文件实际保存到：
   <project-root>/input/codex_generated_pixel_art.png
3. 确认文件存在后，调用 pixel_reforge MCP Server 的 reforge_image，
   不要调用 CLI，也不要模拟处理结果。参数为：
   {
     "source_path": "codex_generated_pixel_art.png",
     "scale": 8,
     "pixel_mode": "detect",
     "sample_method": "center",
     "refine_intensity": 0.3,
     "force": true,
     "archive_source": true
   }
4. 读取工具实际返回的 status、outputs 和 error，并报告 1x、8x 输出绝对路径
   以及原图是否已经移动到 processed/。

不要根据文件命名规则猜测输出路径；如果处理失败，返回真实错误。
```

如果当前 Codex 界面无法在生成图片的同一轮继续调用 MCP，可以拆成两轮：第一轮只生成并保存到 `input/`，第二轮再明确要求使用 `reforge_image` 处理该相对路径。
